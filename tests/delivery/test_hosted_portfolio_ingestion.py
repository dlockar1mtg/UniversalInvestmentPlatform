from datetime import datetime, timezone
import sqlite3

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from foundation.production.hosted_portfolio import install_hosted_portfolio_routes
from foundation.production.http_service import HTTPServiceSettings, create_http_app
from foundation.production.persistence import SQLiteProductionRepository
from foundation.production.portfolio_persistence import SQLitePortfolioSnapshotRepository


HEADER = "position_id,account_id,portfolio_group,asset_type,asset_id,quantity,cost_basis,market_value,currency,as_of,symbol,name,provider_symbol,target_weight,liquidity_class,notes\n"
ROW = "p1,primary,etf,etf,spy,1.25,500,625,USD,2026-07-20T18:00:00Z,SPY,S&P 500,SPY,,liquid,\n"


def client(tmp_path, maximum=262_144):
    production = SQLiteProductionRepository(tmp_path / "production.sqlite3")
    production.initialize()
    settings = HTTPServiceSettings(credentials={
        "viewer": ("view-key", ("viewer",)), "operator": ("operate-key", ("operator",)),
    })
    app = create_http_app(settings, production)
    snapshots = SQLitePortfolioSnapshotRepository(sqlite3.connect(":memory:", check_same_thread=False))
    snapshots.initialize()
    install_hosted_portfolio_routes(app, settings, snapshots, maximum_csv_bytes=maximum)
    return TestClient(app), snapshots


def test_import_requires_operator_and_read_requires_viewer(tmp_path):
    service, _ = client(tmp_path)
    assert service.post("/v1/portfolio/snapshots", content=HEADER + ROW, headers={"Content-Type": "text/csv"}).status_code == 401
    assert service.post("/v1/portfolio/snapshots", content=HEADER + ROW, headers={"Content-Type": "text/csv", "X-API-Key": "view-key"}).status_code == 403
    assert service.get("/v1/portfolio/snapshots/current").status_code == 401
    assert service.get("/v1/portfolio/snapshots/current", headers={"X-API-Key": "view-key"}).status_code == 404


def test_valid_csv_creates_snapshot_and_viewer_reads_exact_positions(tmp_path):
    service, _ = client(tmp_path)
    response = service.post("/v1/portfolio/snapshots", content=HEADER + ROW, headers={
        "Content-Type": "text/csv", "X-API-Key": "operate-key", "X-Correlation-ID": "portfolio-1",
    })
    assert response.status_code == 201 and response.json()["created"] is True
    assert response.headers["X-Correlation-ID"] == "portfolio-1"
    current = service.get("/v1/portfolio/snapshots/current", headers={"X-API-Key": "view-key"}).json()
    assert current["position_count"] == 1
    assert current["positions"][0]["market_value"] == "625"


def test_identical_upload_reuses_snapshot_without_duplicate_history(tmp_path):
    service, repository = client(tmp_path)
    headers = {"Content-Type": "text/csv", "X-API-Key": "operate-key"}
    first = service.post("/v1/portfolio/snapshots", content=HEADER + ROW, headers=headers)
    second = service.post("/v1/portfolio/snapshots", content=HEADER + ROW, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 200 and second.json()["created"] is False
    assert len(repository.history()) == 1


def test_invalid_csv_is_rejected_before_any_database_write(tmp_path):
    service, repository = client(tmp_path)
    response = service.post("/v1/portfolio/snapshots", content=HEADER + ROW.replace("USD", "US"), headers={
        "Content-Type": "text/csv", "X-API-Key": "operate-key",
    })
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PORTFOLIO_INVALID"
    assert repository.latest() is None


def test_content_type_and_bounded_body_are_enforced(tmp_path):
    service, _ = client(tmp_path, maximum=1024)
    assert service.post("/v1/portfolio/snapshots", content=HEADER + ROW, headers={"X-API-Key": "operate-key"}).status_code == 415
    oversized = "x" * 1025
    response = service.post("/v1/portfolio/snapshots", content=oversized, headers={
        "Content-Type": "text/csv", "X-API-Key": "operate-key",
    })
    assert response.status_code == 413


def test_history_is_bounded_and_contains_summaries_only(tmp_path):
    service, _ = client(tmp_path)
    service.post("/v1/portfolio/snapshots", content=HEADER + ROW, headers={"Content-Type": "text/csv", "X-API-Key": "operate-key"})
    history = service.get("/v1/portfolio/snapshots?limit=1", headers={"X-API-Key": "view-key"})
    assert history.status_code == 200 and len(history.json()["items"]) == 1
    assert "positions" not in history.json()["items"][0]
    assert service.get("/v1/portfolio/snapshots?limit=101", headers={"X-API-Key": "view-key"}).status_code == 422


def test_audit_evidence_redacts_credential_and_omits_holdings(tmp_path):
    service, _ = client(tmp_path)
    service.post("/v1/portfolio/snapshots", content=HEADER + ROW, headers={
        "Content-Type": "text/csv", "X-API-Key": "operate-key", "X-Correlation-ID": "audit-import",
    })
    event = service.app.state.events.events[-1]
    assert event.event_type == "PORTFOLIO_SNAPSHOT_CREATED"
    assert event.fields["credential"] == "[REDACTED]"
    assert "S&P 500" not in str(event.fields) and "operate-key" not in str(event.fields)
