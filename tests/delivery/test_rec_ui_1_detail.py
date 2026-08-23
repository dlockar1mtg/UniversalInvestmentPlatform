from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundation.presentation.recommendation_detail import (
    install_recommendation_detail_routes,
)


ROOT = Path(__file__).resolve().parents[2]


class FakeRecommendationDetailRepository:
    def detail(self, *, domain_id, asset_id):
        domain = domain_id.strip().lower()
        asset = asset_id.strip()
        if domain not in {"crypto", "metals", "mtg"} or asset == "missing":
            raise LookupError("Recommendation not present in active presentation")
        return {
            "publication_id": "pub-1",
            "domain_id": domain,
            "asset_id": asset,
            "record_key": asset,
            "asset_name": "Example asset",
            "asset_symbol": None,
            "asset_subclass": "SECRET_LAIR_V1_1" if domain == "mtg" else None,
            "current_price_usd": "137.62" if domain == "mtg" else None,
            "current_price_authority_available": domain == "mtg",
            "native_status": "BUY_CANDIDATE_NOW" if domain == "mtg" else "watch",
            "native_status_source_field": "native_purchase_status" if domain == "mtg" else "native_recommendation",
            "confidence_score": None,
            "native_rank": 10 if domain == "mtg" else None,
            "native_rank_type": "SECRET_LAIR_V1_1_PRODUCTION_COMPETITION_RANK" if domain == "mtg" else None,
            "manual_execution_price_check_required": True if domain == "mtg" else None,
            "automatic_purchase_execution": False,
            "recommendation_payload": {"native_purchase_status": "BUY_CANDIDATE_NOW"} if domain == "mtg" else {"native_recommendation": "watch"},
            "asset_payload": {"asset_name": "Example asset"},
            "forecast_records": [{"record_key": "f-1", "payload": {"native_horizon": "example"}}],
            "risk_records": [],
            "domain_native_semantics": True,
            "universal_cross_domain_rank": False,
            "rank_comparison_scope": "NATIVE_RANK_TYPE_ONLY",
            "missing_fields_policy": "PRESERVE_MISSING",
        }


def client():
    app = FastAPI()
    install_recommendation_detail_routes(
        app,
        {
            "viewer": ("view-key", ("viewer",)),
            "operator": ("operate-key", ("operator",)),
        },
        FakeRecommendationDetailRepository(),
    )
    return TestClient(app)


def test_detail_requires_auth_domain_and_asset_identity():
    service = client()
    assert service.get(
        "/v1/presentation/recommendation-detail?domain=mtg&asset_id=asset-1"
    ).status_code == 401
    assert service.get(
        "/v1/presentation/recommendation-detail?domain=mtg",
        headers={"X-API-Key": "view-key"},
    ).status_code == 422
    assert service.get(
        "/v1/presentation/recommendation-detail?asset_id=asset-1",
        headers={"X-API-Key": "view-key"},
    ).status_code == 422


def test_detail_preserves_native_payload_forecast_risk_and_missing_fields():
    response = client().get(
        "/v1/presentation/recommendation-detail?domain=mtg&asset_id=asset-1",
        headers={"X-API-Key": "view-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["domain_id"] == "mtg"
    assert body["asset_id"] == "asset-1"
    assert body["native_status"] == "BUY_CANDIDATE_NOW"
    assert body["native_rank"] == 10
    assert body["native_rank_type"] == "SECRET_LAIR_V1_1_PRODUCTION_COMPETITION_RANK"
    assert body["manual_execution_price_check_required"] is True
    assert body["automatic_purchase_execution"] is False
    assert body["forecast_records"] == [
        {"record_key": "f-1", "payload": {"native_horizon": "example"}}
    ]
    assert body["risk_records"] == []
    assert body["domain_native_semantics"] is True
    assert body["universal_cross_domain_rank"] is False
    assert body["rank_comparison_scope"] == "NATIVE_RANK_TYPE_ONLY"
    assert body["missing_fields_policy"] == "PRESERVE_MISSING"


def test_detail_missing_identity_fails_closed():
    response = client().get(
        "/v1/presentation/recommendation-detail?domain=mtg&asset_id=missing",
        headers={"X-API-Key": "view-key"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RECOMMENDATION_NOT_IN_ACTIVE_PRESENTATION"


def test_production_detail_contract_preserves_domain_native_records_and_no_execution():
    source = (
        ROOT
        / "foundation"
        / "presentation"
        / "recommendation_detail.py"
    ).read_text(encoding="utf-8")
    runtime = (ROOT / "scripts" / "run_production_api.py").read_text(encoding="utf-8")

    for marker in (
        "recommendation_payload",
        "asset_payload",
        "forecast_records",
        "risk_records",
        "native_purchase_status",
        "native_recommendation",
        "native_rank",
        "native_rank_type",
        "manual_execution_price_check_required",
        "automatic_purchase_execution",
        '"domain_native_semantics": True',
        '"universal_cross_domain_rank": False',
        '"rank_comparison_scope": "NATIVE_RANK_TYPE_ONLY"',
        '"missing_fields_policy": "PRESERVE_MISSING"',
    ):
        assert marker in source

    assert 'app.get("/v1/presentation/recommendation-detail")' in source
    assert "ORDER BY record_key" in source
    assert "install_recommendation_detail_routes" in runtime
