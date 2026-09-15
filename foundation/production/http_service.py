"""FastAPI transport and operational dashboard for the production boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from fastapi import FastAPI, Header, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from .api import ProductionAPI
from .dashboard import DashboardService, DashboardSettings
from .observability import EventRecorder, MetricRegistry, SecuredProductionGateway
from .persistence import SQLiteProductionRepository
from .postgres import PostgresProductionRepository
from .security import APIKeyAuthenticator, Permission


@dataclass(frozen=True)
class HTTPServiceSettings:
    database_backend: str = "sqlite"
    database_url: str = ""
    sqlite_path: Path = Path("var/uiip/production.sqlite3")
    credentials: Mapping[str, tuple[str, tuple[str, ...]]] = None

    def __post_init__(self) -> None:
        if self.database_backend not in {"sqlite", "postgresql"}:
            raise ValueError("database backend must be sqlite or postgresql")
        if self.database_backend == "postgresql" and not self.database_url.strip():
            raise ValueError("PostgreSQL backend requires database_url")
        if self.credentials is None:
            object.__setattr__(self, "credentials", {})

    @classmethod
    def from_environment(cls, values: Mapping[str, str] = os.environ):
        backend = values.get("UIIP_DATABASE_BACKEND", "sqlite").lower()
        try:
            document = json.loads(values.get("UIIP_API_CREDENTIALS_JSON", "{}"))
            if not isinstance(document, dict):
                raise ValueError
            credentials = {
                str(principal_id): (str(definition["credential"]), tuple(str(role) for role in definition["roles"]))
                for principal_id, definition in document.items()
            }
        except (TypeError, KeyError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("UIIP_API_CREDENTIALS_JSON must contain principal credential and roles mappings") from exc
        return cls(backend, values.get("UIIP_DATABASE_URL", ""), Path(values.get("UIIP_SQLITE_PATH", "var/uiip/production.sqlite3")), credentials)


def build_repository(settings: HTTPServiceSettings):
    if settings.database_backend == "postgresql":
        repository = PostgresProductionRepository.from_dsn(settings.database_url)
    else:
        settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        repository = SQLiteProductionRepository(settings.sqlite_path)
    repository.initialize()
    return repository


def create_http_app(settings: HTTPServiceSettings, repository=None, dashboard_settings: DashboardSettings | None = None) -> FastAPI:
    repository = repository or build_repository(settings)
    principals, hashes = {}, {}
    for principal_id, (credential, roles) in sorted(settings.credentials.items()):
        principals[principal_id] = roles
        hashes[principal_id] = APIKeyAuthenticator.hash_credential(credential)
    authenticator = APIKeyAuthenticator(principals, hashes)
    events, metrics = EventRecorder(), MetricRegistry()
    gateway = SecuredProductionGateway(ProductionAPI(repository), authenticator, events, metrics)
    dashboard = DashboardService(repository, events, metrics, dashboard_settings or DashboardSettings.from_environment())
    assets = Path(__file__).resolve().parent / "dashboard_assets"
    app = FastAPI(title="Universal Investment Platform", version="7.4.0")
    app.state.repository, app.state.events, app.state.metrics = repository, events, metrics
    app.state.dashboard = dashboard

    @app.get("/health/live")
    def live():
        return {"status": "LIVE"}

    @app.get("/health/ready")
    def ready():
        available = repository.readiness() if hasattr(repository, "readiness") else True
        return JSONResponse({"status": "READY" if available else "NOT_READY"}, status_code=200 if available else 503)

    @app.get("/dashboard", include_in_schema=False)
    def dashboard_page():
        return FileResponse(assets / "dashboard.html", media_type="text/html")

    @app.get("/dashboard/assets/dashboard.css", include_in_schema=False)
    def dashboard_css():
        return FileResponse(assets / "dashboard.css", media_type="text/css")

    @app.get("/dashboard/assets/recommendation_visual.css", include_in_schema=False)
    def recommendation_visual_css():
        return FileResponse(assets / "recommendation_visual.css", media_type="text/css")

    @app.get("/dashboard/assets/metals_visual.css", include_in_schema=False)
    def metals_visual_css():
        return FileResponse(assets / "metals_visual.css", media_type="text/css")

    @app.get("/dashboard/assets/dashboard.js", include_in_schema=False)
    def dashboard_javascript():
        return FileResponse(assets / "dashboard.js", media_type="text/javascript")

    @app.get("/dashboard/assets/recommendation_ui.js", include_in_schema=False)
    def recommendation_ui_javascript():
        return FileResponse(assets / "recommendation_ui.js", media_type="text/javascript")

    @app.get("/dashboard/assets/metals_tactical_ui.js", include_in_schema=False)
    def metals_tactical_ui_javascript():
        return FileResponse(assets / "metals_tactical_ui.js", media_type="text/javascript")

    @app.get("/dashboard/assets/metals_vehicle_ui.js", include_in_schema=False)
    def metals_vehicle_ui_javascript():
        return FileResponse(assets / "metals_vehicle_ui.js", media_type="text/javascript")

    @app.get("/dashboard/assets/governed_asset_picker.js", include_in_schema=False)
    def governed_asset_picker_javascript():
        return FileResponse(assets / "governed_asset_picker.js", media_type="text/javascript")

    def dashboard_authorization(credential: str | None):
        principal = authenticator.authenticate(credential)
        if principal is None:
            return JSONResponse({"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}}, status_code=401)
        if not principal.permits(Permission.RUN_READ):
            return JSONResponse({"error": {"code": "FORBIDDEN", "message": "read permission is required"}}, status_code=403)
        return None

    @app.get("/v1/dashboard/summary")
    def dashboard_summary(x_api_key: str | None = Header(default=None)):
        denied = dashboard_authorization(x_api_key)
        return denied or dashboard.summary()

    @app.get("/v1/dashboard/events")
    def dashboard_events(limit: int = Query(default=50, ge=1, le=200), x_api_key: str | None = Header(default=None)):
        denied = dashboard_authorization(x_api_key)
        return denied or {"items": dashboard.event_documents(limit)}

    @app.get("/v1/dashboard/metrics")
    def dashboard_metrics(x_api_key: str | None = Header(default=None)):
        denied = dashboard_authorization(x_api_key)
        return denied or dashboard.metric_document()

    async def dispatch(request: Request, x_api_key: str | None, x_correlation_id: str | None):
        body = await request.body() if request.method == "POST" else None
        correlation = x_correlation_id or str(uuid4())
        response = gateway.handle(request.method, request.url.path, body, credential=x_api_key, correlation_id=correlation)
        return JSONResponse(dict(response.body), status_code=response.status_code, headers={"X-Correlation-ID": correlation})

    @app.post("/v1/runs")
    async def submit(request: Request, x_api_key: str | None = Header(default=None), x_correlation_id: str | None = Header(default=None)):
        return await dispatch(request, x_api_key, x_correlation_id)

    @app.get("/v1/runs/{run_id}")
    async def get_run(run_id: str, request: Request, x_api_key: str | None = Header(default=None), x_correlation_id: str | None = Header(default=None)):
        return await dispatch(request, x_api_key, x_correlation_id)

    return app
