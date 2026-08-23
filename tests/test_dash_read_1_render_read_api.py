from datetime import datetime, timezone

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundation.presentation.read_api import install_presentation_read_routes


class FakePresentationReadRepository:
    def active_metadata(self):
        return {
            "publication_id": "pub-1",
            "publication_version": "1.0.0",
            "source_database_sha256": "a" * 64,
            "source_database_classification": "AUTHORITATIVE_MULTI_DOMAIN_PRODUCTION_STATE_R3_CERTIFIED",
            "published_at_utc": datetime(2026, 8, 23, tzinfo=timezone.utc),
            "publication_status": "ACTIVE",
            "content_fingerprint": "b" * 64,
            "record_count": 4031,
            "activated_at_utc": datetime(2026, 8, 23, 1, tzinfo=timezone.utc),
        }

    def domain_health(self):
        return (
            {"domain_id": "crypto", "certification_state": "CERTIFIED"},
            {"domain_id": "metals", "certification_state": "CERTIFIED"},
            {"domain_id": "mtg", "certification_state": "CERTIFIED"},
        )

    def recommendations(self, *, domain_id, limit, offset):
        items = (
            {"domain_id": "crypto", "asset_id": "crypto:bitcoin", "record_key": "crypto:bitcoin", "payload": {"native_recommendation": "watch", "cross_domain_rank": None}},
            {"domain_id": "mtg", "asset_id": "mtg:1", "record_key": "mtg:1", "payload": {"native_purchase_status": "BUY_CANDIDATE_NOW", "native_rank": 12, "automatic_purchase_execution": False}},
        )
        if domain_id is not None:
            items = tuple(item for item in items if item["domain_id"] == domain_id)
        return items[offset:offset + limit]

    def asset_detail(self, domain_id, asset_id):
        if (domain_id, asset_id) != ("mtg", "mtg:1"):
            return None
        return {
            "domain_id": "mtg",
            "asset_id": "mtg:1",
            "records": {
                "asset": [{"record_key": "mtg:1", "payload": {"current_price_usd": 36.0, "current_price_authority_available": True}}],
                "recommendation": [{"record_key": "mtg:1", "payload": {"native_rank": 12, "automatic_purchase_execution": False}}],
            },
        }

    def lineage(self, domain_id, asset_id):
        if (domain_id, asset_id) != ("mtg", "mtg:1"):
            return None
        return {
            "domain_id": "mtg",
            "asset_id": "mtg:1",
            "items": [{"record_type": "asset", "record_key": "mtg:1", "lineage": {"_package_id": "pkg-1", "_import_id": "imp-1"}}],
        }


def client():
    app = FastAPI()
    install_presentation_read_routes(
        app,
        {"viewer": ("view-key", ("viewer",)), "operator": ("operate-key", ("operator",))},
        FakePresentationReadRepository(),
    )
    return TestClient(app)


def test_presentation_endpoints_require_read_permission():
    service = client()
    assert service.get("/v1/presentation/status").status_code == 401
    assert service.get("/v1/presentation/status", headers={"X-API-Key": "view-key"}).status_code == 200


def test_status_exposes_active_publication_provenance():
    response = client().get("/v1/presentation/status", headers={"X-API-Key": "view-key"})
    body = response.json()
    assert body["publication_id"] == "pub-1"
    assert body["publication_status"] == "ACTIVE"
    assert body["record_count"] == 4031
    assert body["source_database_sha256"] == "a" * 64


def test_domain_health_returns_exact_certified_domain_set():
    response = client().get("/v1/presentation/domain-health", headers={"X-API-Key": "view-key"})
    assert [item["domain_id"] for item in response.json()["items"]] == ["crypto", "metals", "mtg"]


def test_recommendations_preserve_native_semantics_and_support_domain_filter():
    service = client()
    response = service.get("/v1/presentation/recommendations?domain=mtg", headers={"X-API-Key": "view-key"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["payload"]["native_rank"] == 12
    assert items[0]["payload"]["automatic_purchase_execution"] is False
    assert service.get("/v1/presentation/recommendations?domain=etf", headers={"X-API-Key": "view-key"}).status_code == 400


def test_asset_detail_and_lineage_are_read_only_active_projection_views():
    service = client()
    detail = service.get("/v1/presentation/assets/mtg/mtg:1", headers={"X-API-Key": "view-key"})
    assert detail.status_code == 200
    assert detail.json()["records"]["asset"][0]["payload"]["current_price_usd"] == 36.0
    lineage = service.get("/v1/presentation/lineage/mtg/mtg:1", headers={"X-API-Key": "view-key"})
    assert lineage.status_code == 200
    assert lineage.json()["items"][0]["lineage"]["_package_id"] == "pkg-1"
    assert service.get("/v1/presentation/assets/crypto/missing", headers={"X-API-Key": "view-key"}).status_code == 404
