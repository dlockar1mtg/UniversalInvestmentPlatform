from datetime import datetime, timezone
import json

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from foundation.production import HTTPServiceSettings, SQLiteProductionRepository, create_http_app

NOW = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)


def client(tmp_path):
    repository = SQLiteProductionRepository(tmp_path / "service.sqlite3")
    repository.initialize()
    settings = HTTPServiceSettings(credentials={"viewer": ("view-key", ("viewer",)), "operator": ("operate-key", ("operator",))})
    return TestClient(create_http_app(settings, repository)), repository


def payload(run_id="run-1"):
    return {"run_id": run_id, "source_phase": "6", "policy_fingerprint": "a" * 64, "requested_at": NOW.isoformat(), "payload": {"portfolio": "universal"}}


def test_liveness_and_readiness_are_public_and_healthy(tmp_path):
    service, _ = client(tmp_path)
    assert service.get("/health/live").json() == {"status": "LIVE"}
    assert service.get("/health/ready").json() == {"status": "READY"}


def test_submit_requires_operator_permission(tmp_path):
    service, _ = client(tmp_path)
    assert service.post("/v1/runs", json=payload()).status_code == 401
    assert service.post("/v1/runs", json=payload(), headers={"X-API-Key": "view-key"}).status_code == 403
    assert service.post("/v1/runs", json=payload(), headers={"X-API-Key": "operate-key"}).status_code == 202


def test_submitted_run_is_durable_and_readable_by_viewer(tmp_path):
    service, repository = client(tmp_path)
    response = service.post("/v1/runs", json=payload(), headers={"X-API-Key": "operate-key", "X-Correlation-ID": "correlation-1"})
    assert response.headers["X-Correlation-ID"] == "correlation-1"
    assert repository.get_run("run-1").run_id == "run-1"
    found = service.get("/v1/runs/run-1", headers={"X-API-Key": "view-key"})
    assert found.status_code == 200 and found.json()["status"] == "REGISTERED"


def test_http_errors_remain_structured_and_do_not_leak_credentials(tmp_path):
    service, _ = client(tmp_path)
    response = service.get("/v1/runs/missing", headers={"X-API-Key": "view-key"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"
    assert "view-key" not in response.text


def test_environment_settings_select_explicit_backends(tmp_path):
    sqlite = HTTPServiceSettings.from_environment({"UIIP_DATABASE_BACKEND": "sqlite", "UIIP_SQLITE_PATH": str(tmp_path / "local.sqlite3")})
    postgres = HTTPServiceSettings.from_environment({"UIIP_DATABASE_BACKEND": "postgresql", "UIIP_DATABASE_URL": "postgresql://example/db"})
    assert sqlite.database_backend == "sqlite" and sqlite.sqlite_path.name == "local.sqlite3"
    assert postgres.database_backend == "postgresql"
    with pytest.raises(ValueError, match="requires database_url"):
        HTTPServiceSettings(database_backend="postgresql")


def test_service_records_correlated_redacted_events_and_metrics(tmp_path):
    service, _ = client(tmp_path)
    service.get("/v1/runs/missing", headers={"X-API-Key": "view-key", "X-Correlation-ID": "audit-correlation"})
    event = service.app.state.events.events[0]
    assert event.correlation_id == "audit-correlation"
    assert event.fields["credential"] == "[REDACTED]"
    assert service.app.state.metrics.snapshot()["counters"][0]["value"] == 1
