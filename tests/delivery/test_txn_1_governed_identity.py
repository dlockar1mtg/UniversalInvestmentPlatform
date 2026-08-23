import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from foundation.presentation.asset_catalog import install_governed_asset_catalog_routes
from foundation.production.hosted_transactions import install_hosted_transaction_routes
from foundation.production.http_service import HTTPServiceSettings, create_http_app
from foundation.production.persistence import SQLiteProductionRepository
from foundation.production.transaction_persistence import SQLiteTransactionRepository


class FakeCatalog:
    def domains(self):
        return ("crypto", "metals", "mtg")

    def search_assets(self, *, domain_id, query="", limit=50):
        rows = {
            "crypto": (
                {"domain_id": "crypto", "asset_id": "crypto:bitcoin", "asset_name": "Bitcoin", "asset_symbol": "BTC", "asset_class": "crypto", "asset_subclass": None},
            ),
            "metals": (
                {"domain_id": "metals", "asset_id": "metals:gold", "asset_name": "Gold", "asset_symbol": "XAU", "asset_class": "metals", "asset_subclass": None},
            ),
            "mtg": (
                {"domain_id": "mtg", "asset_id": "mtg:secret-lair:test", "asset_name": "Secret Lair Test Product", "asset_symbol": None, "asset_class": None, "asset_subclass": "secret_lair"},
            ),
        }.get(domain_id, ())
        term = query.lower().strip()
        return tuple(item for item in rows if not term or term in (item["asset_name"] + " " + item["asset_id"] + " " + str(item.get("asset_symbol") or "")).lower())[:limit]

    def asset_exists(self, domain_id, asset_id):
        return any(item["asset_id"] == asset_id for item in self.search_assets(domain_id=domain_id, query="", limit=100))


def _settings():
    return HTTPServiceSettings(credentials={
        "viewer": ("view-key", ("viewer",)),
        "operator": ("operate-key", ("operator",)),
    })


def _service(tmp_path):
    production = SQLiteProductionRepository(tmp_path / "production.sqlite3")
    production.initialize()
    settings = _settings()
    app = create_http_app(settings, production)
    catalog = FakeCatalog()
    install_governed_asset_catalog_routes(app, settings.credentials, catalog)
    ledger = SQLiteTransactionRepository(sqlite3.connect(":memory:", check_same_thread=False))
    ledger.initialize()
    install_hosted_transaction_routes(
        app,
        settings,
        ledger,
        asset_identity_validator=catalog.asset_exists,
    )
    return TestClient(app), ledger


def _payload(**overrides):
    payload = {
        "transaction_type": "BUY",
        "domain_id": "crypto",
        "asset_id": "crypto:bitcoin",
        "occurred_at": "2026-08-23T00:30:00-05:00",
        "quantity": "0.01",
        "price_per_unit": "64000",
        "fees": "0",
        "currency": "USD",
        "account_id": "wallet",
        "venue": "",
        "external_reference": "",
        "notes": "",
    }
    payload.update(overrides)
    return payload


def test_asset_catalog_requires_auth_and_returns_governed_domains_and_search(tmp_path):
    service, _ = _service(tmp_path)
    assert service.get("/v1/presentation/domains").status_code == 401
    domains = service.get("/v1/presentation/domains", headers={"X-API-Key": "view-key"})
    assert domains.status_code == 200
    assert [item["domain_id"] for item in domains.json()["items"]] == ["crypto", "metals", "mtg"]
    assets = service.get(
        "/v1/presentation/assets?domain=mtg&query=secret&limit=50",
        headers={"X-API-Key": "view-key"},
    )
    assert assets.status_code == 200
    assert assets.json()["items"][0]["asset_id"] == "mtg:secret-lair:test"


def test_transaction_rejects_free_text_identity_not_in_active_catalog(tmp_path):
    service, ledger = _service(tmp_path)
    rejected = service.post(
        "/v1/transactions",
        json=_payload(asset_id="Bitcoin typed by hand"),
        headers={"X-API-Key": "operate-key"},
    )
    assert rejected.status_code == 422
    assert "active certified UIP asset catalog" in rejected.json()["error"]["message"]
    assert ledger.list(limit=10, offset=0) == ()


def test_transaction_accepts_exact_governed_identity(tmp_path):
    service, ledger = _service(tmp_path)
    created = service.post(
        "/v1/transactions",
        json=_payload(),
        headers={"X-API-Key": "operate-key"},
    )
    assert created.status_code == 201
    item = created.json()["transaction"]
    assert item["domain_id"] == "crypto"
    assert item["asset_id"] == "crypto:bitcoin"
    assert item["metadata"]["identity_source"] == "active-certified-asset-catalog"
    assert len(ledger.list(limit=10, offset=0)) == 1


def test_dashboard_loads_governed_picker_asset_and_uses_catalog_routes():
    root = Path(__file__).resolve().parents[2]
    html = (root / "foundation" / "production" / "dashboard_assets" / "dashboard.html").read_text(encoding="utf-8")
    picker = (root / "foundation" / "production" / "dashboard_assets" / "governed_asset_picker.js").read_text(encoding="utf-8")
    assert "/dashboard/assets/governed_asset_picker.js" in html
    assert "/v1/presentation/domains" in picker
    assert "/v1/presentation/assets?domain=" in picker
    assert "Choose an exact governed asset" in picker
    assert 'document.addEventListener("submit",event=>' in picker
    assert "if(event.target!==form)return" in picker
    assert "const canonicalAssetId=String(selected.asset_id)" in picker
    assert "assetInput.value=canonicalAssetId" in picker
