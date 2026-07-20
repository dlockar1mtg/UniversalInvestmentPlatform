import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from foundation.production.hosted_portfolio import install_hosted_portfolio_routes
from foundation.production.http_service import HTTPServiceSettings, create_http_app
from foundation.production.persistence import SQLiteProductionRepository
from foundation.production.portfolio_persistence import SQLitePortfolioSnapshotRepository


HEADER = "position_id,account_id,portfolio_group,asset_type,asset_id,quantity,cost_basis,market_value,currency,as_of,symbol,name,provider_symbol,target_weight,liquidity_class,notes\n"


def _client(tmp_path):
    production = SQLiteProductionRepository(tmp_path / "production.sqlite3")
    production.initialize()
    settings = HTTPServiceSettings(credentials={"operator": ("operate-key", ("operator",))})
    app = create_http_app(settings, production)
    snapshots = SQLitePortfolioSnapshotRepository(sqlite3.connect(":memory:", check_same_thread=False))
    snapshots.initialize()
    install_hosted_portfolio_routes(app, settings, snapshots)
    return TestClient(app), snapshots


def test_header_only_csv_returns_controlled_validation_error_without_a_write(tmp_path):
    service, repository = _client(tmp_path)
    response = service.post(
        "/v1/portfolio/snapshots",
        content=HEADER,
        headers={"Content-Type": "text/csv", "X-API-Key": "operate-key"},
    )
    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "PORTFOLIO_INVALID", "message": "portfolio CSV failed validation"},
        "errors": [{"field": "portfolio", "message": "at least one position is required", "row_number": 2}],
    }
    assert repository.latest() is None
    event = service.app.state.events.events[-1]
    assert event.event_type == "PORTFOLIO_IMPORT_REJECTED"
    assert event.fields["credential"] == "[REDACTED]"


def test_print_styles_remove_layout_height_that_can_create_a_blank_trailing_page():
    root = Path(__file__).resolve().parents[2]
    css = (root / "foundation" / "production" / "dashboard_assets" / "dashboard.css").read_text(encoding="utf-8")
    assert "html,body{height:auto!important;min-height:0!important}" in css
    assert "main{padding-bottom:0!important}" in css
    assert ".grid .panel{min-height:0!important}" in css
