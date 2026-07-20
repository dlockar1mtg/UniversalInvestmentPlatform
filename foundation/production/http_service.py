"""FastAPI transport for the certified production service boundary."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from .api import ProductionAPI
from .observability import EventRecorder, MetricRegistry, SecuredProductionGateway
from .persistence import SQLiteProductionRepository
from .postgres import PostgresProductionRepository
from .security import APIKeyAuthenticator


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
        return cls(backend, values.get("UIIP_DATABASE_URL", ""), Path(values.get("UIIP_SQLITE_PATH", "var/uiip/production.sqlite3")))


def build_repository(settings: HTTPServiceSettings):
    if settings.database_backend == "postgresql":
        repository = PostgresProductionRepository.from_dsn(settings.database_url)
    else:
        settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        repository = SQLiteProductionRepository(settings.sqlite_path)
    repository.initialize()
    return repository


def create_http_app(settings: HTTPServiceSettings, repository=None) -> FastAPI:
    repository = repository or build_repository(settings)
    principals, hashes = {}, {}
    for principal_id, (credential, roles) in sorted(settings.credentials.items()):
        principals[principal_id] = roles
        hashes[principal_id] = APIKeyAuthenticator.hash_credential(credential)
    authenticator = APIKeyAuthenticator(principals, hashes)
    events, metrics = EventRecorder(), MetricRegistry()
    gateway = SecuredProductionGateway(ProductionAPI(repository), authenticator, events, metrics)
    app = FastAPI(title="Universal Investment Platform", version="7.1.0")
    app.state.repository, app.state.events, app.state.metrics = repository, events, metrics

    @app.get("/health/live")
    def live():
        return {"status": "LIVE"}

    @app.get("/health/ready")
    def ready():
        available = repository.readiness() if hasattr(repository, "readiness") else True
        return JSONResponse({"status": "READY" if available else "NOT_READY"}, status_code=200 if available else 503)

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
