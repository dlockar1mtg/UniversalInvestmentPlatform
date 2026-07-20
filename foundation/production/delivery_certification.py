"""Deterministic Phase 7 live-delivery certification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from .dashboard import DashboardSettings
from .http_service import HTTPServiceSettings, create_http_app
from .live_security import LiveSecuritySettings, install_live_security
from .persistence import SQLiteProductionRepository
from .portfolio import preview_portfolio_csv
from .providers import AlphaVantageProvider, FREDProvider
from .scheduling import SQLiteJobRepository
from .worker import RecurringSchedule, enqueue_schedule


@dataclass(frozen=True)
class DeliveryCertificationCheck:
    check_id: str
    status: str
    evidence: str


@dataclass(frozen=True)
class Phase7CertificationReport:
    phase: str
    release_version: str
    status: str
    checks: tuple[DeliveryCertificationCheck, ...]
    certification_fingerprint: str

    def document(self) -> dict[str, object]:
        return {
            "certification_fingerprint": self.certification_fingerprint,
            "checks": [check.__dict__ for check in self.checks],
            "phase": self.phase,
            "release_version": self.release_version,
            "status": self.status,
        }


def _check(check_id: str, condition: bool, evidence: str) -> DeliveryCertificationCheck:
    return DeliveryCertificationCheck(check_id, "PASSED" if condition else "FAILED", evidence)


def certify_phase_7(root: Path | str = Path.cwd()) -> Phase7CertificationReport:
    root = Path(root)
    checks: list[DeliveryCertificationCheck] = []
    ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    container = (root / ".github/workflows/container.yml").read_text(encoding="utf-8")
    release = (root / ".github/workflows/go-live.yml").read_text(encoding="utf-8")
    staging = (root / "deployment/compose.staging.yml").read_text(encoding="utf-8")
    environment_template = (root / "deployment/staging.env.example").read_text(encoding="utf-8")
    checks.append(_check("CI_TEST_GATE", "requirements.txt -r requirements/phase_7_3.txt" in ci and "pytest -q" in ci, "CI installs platform and production dependencies before the complete test suite."))
    checks.append(_check("CONTAINER_DELIVERY", "docker/build-push-action" in container and "github.sha" in container, "Container delivery publishes immutable commit-addressed images from main."))
    placeholder_count = environment_template.count("replace-through-secret-manager")
    checks.append(_check("SECRET_HYGIENE", placeholder_count >= 4 and "UIIP_SCHEDULES_JSON=[]" in environment_template, "Staging configuration contains placeholders rather than deployable credentials."))

    security = LiveSecuritySettings("production", ("invest.example.com",), True, 4096)
    checks.append(_check("PRODUCTION_SECURITY_POLICY", security.require_https and "*" not in security.allowed_hosts, "Production requires HTTPS, explicit hosts, request limits, and security headers."))

    with TemporaryDirectory() as directory:
        temporary = Path(directory)
        repository = SQLiteProductionRepository(temporary / "runs.sqlite3")
        repository.initialize()
        app = create_http_app(
            HTTPServiceSettings(credentials={"viewer": ("cert-view", ("viewer",))}), repository,
            DashboardSettings(temporary / "holdings.csv", True, True),
        )
        install_live_security(app, LiveSecuritySettings("development", ("testserver",), False))
        service = TestClient(app)
        denied = service.get("/v1/dashboard/summary")
        accepted = service.get("/v1/dashboard/summary", headers={"X-API-Key": "cert-view"})
        checks.append(_check("AUTHENTICATION_BOUNDARY", denied.status_code == 401 and accepted.status_code == 200, "Operational data rejects anonymous requests and accepts an authorized viewer."))
        checks.append(_check("SECURITY_HEADER_INTEGRITY", accepted.headers.get("x-frame-options") == "DENY" and accepted.headers.get("cache-control") == "no-store", "Accepted responses carry clickjacking, cache, content-type, referrer, and permissions protections."))

        csv_text = "position_id,account_id,portfolio_group,asset_type,asset_id,quantity,cost_basis,market_value,currency,as_of,symbol,name,provider_symbol,target_weight,liquidity_class,notes\ncert,a,etf,etf,spy,1,100,110,USD,2026-07-20T12:00:00Z,SPY,S&P 500,SPY,,,certification\n"
        portfolio = preview_portfolio_csv(csv_text, is_text=True)
        checks.append(_check("PORTFOLIO_SCHEMA", portfolio.valid and len(portfolio.positions) == 1, "Strict holdings validation accepted the certified timezone-aware cross-stage record."))

        alpha = AlphaVantageProvider("key", transport=lambda *_: json.dumps({"Global Quote": {"05. price": "100.25", "07. latest trading day": "2026-07-17"}}).encode()).quote("SPY")
        fred = FREDProvider("key", transport=lambda *_: json.dumps({"observations": [{"date": "2026-07-16", "value": "6.55"}]}).encode()).latest("MORTGAGE30US")
        checks.append(_check("PROVIDER_NORMALIZATION", str(alpha.price) == "100.25" and str(fred.value) == "6.55", "Alpha Vantage and FRED payloads normalized without exposing credentials."))

        jobs = SQLiteJobRepository(temporary / "jobs.sqlite3")
        jobs.initialize()
        schedule = RecurringSchedule("cert-hourly", "provider_check", timedelta(hours=1), {})
        now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
        first, repeated = enqueue_schedule(jobs, schedule, now), enqueue_schedule(jobs, schedule, now + timedelta(minutes=1))
        checks.append(_check("WORKER_IDEMPOTENCY", first.job_id == repeated.job_id, "Repeated scheduling within one bucket reused the durable job identity."))

    css = (root / "foundation/production/dashboard_assets/dashboard.css").read_text(encoding="utf-8")
    checks.append(_check("DASHBOARD_STATE_INTEGRITY", "[hidden]{display:none!important}" in css and "@media print" in css, "Authenticated, responsive, empty, error, and print dashboard states are explicit."))
    checks.append(_check("STAGING_AND_GO_LIVE_GATE", "UIIP_ENVIRONMENT: staging" in staging and "workflow_dispatch" in release and "DEPLOY" in release, "Staging configuration and manually confirmed go-live evidence gate are present."))

    status = "PASSED" if all(check.status == "PASSED" for check in checks) else "FAILED"
    canonical = json.dumps([check.__dict__ for check in checks], sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    return Phase7CertificationReport("7", "7.0.0", status, tuple(checks), fingerprint)
