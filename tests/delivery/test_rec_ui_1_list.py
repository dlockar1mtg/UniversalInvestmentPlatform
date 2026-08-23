from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundation.presentation.recommendation_list import (
    install_recommendation_list_routes,
)


ROOT = Path(__file__).resolve().parents[2]


class FakeRecommendationListRepository:
    def list(
        self,
        *,
        domain_id,
        limit,
        offset,
        query=None,
        native_status=None,
        native_rank_type=None,
        has_forecast=None,
        has_risk=None,
        current_price_authority_available=None,
        manual_execution_price_check_required=None,
    ):
        domain = domain_id.strip().lower()
        if domain not in {"crypto", "metals", "mtg"}:
            raise LookupError(f"No recommendations for domain '{domain}' in active presentation")
        item = {
            "domain_id": domain,
            "asset_id": "asset-1",
            "record_key": "asset-1",
            "asset_name": "Example asset",
            "asset_symbol": "EX",
            "asset_subclass": None,
            "native_status": "watch" if domain == "crypto" else "BUY",
            "native_status_source_field": "native_recommendation",
            "confidence_score": "0.8",
            "native_rank": None,
            "native_rank_type": None,
            "current_price_usd": None,
            "current_price_authority_available": False,
            "manual_execution_price_check_required": None,
            "automatic_purchase_execution": False,
            "forecast_record_count": 1,
            "risk_record_count": 1,
            "recommendation_payload": {"native_recommendation": "watch"},
        }
        return {
            "publication_id": "pub-1",
            "domain_id": domain,
            "total": 1,
            "limit": limit,
            "offset": offset,
            "query": query,
            "filters": {
                "native_status": native_status,
                "native_rank_type": native_rank_type,
                "has_forecast": has_forecast,
                "has_risk": has_risk,
                "current_price_authority_available": current_price_authority_available,
                "manual_execution_price_check_required": manual_execution_price_check_required,
            },
            "items": [item],
            "domain_native_semantics": True,
            "universal_cross_domain_rank": False,
            "ordering_policy": "STABLE_ASSET_IDENTITY_NOT_NATIVE_RANK",
            "rank_comparison_scope": "NATIVE_RANK_TYPE_ONLY",
            "automatic_execution": False,
            "missing_fields_policy": "PRESERVE_MISSING",
        }


def client():
    app = FastAPI()
    install_recommendation_list_routes(
        app,
        {
            "viewer": ("view-key", ("viewer",)),
            "operator": ("operate-key", ("operator",)),
        },
        FakeRecommendationListRepository(),
    )
    return TestClient(app)


def test_list_requires_auth_and_domain_and_never_returns_cross_domain_rank():
    service = client()
    assert service.get("/v1/presentation/recommendation-list?domain=crypto").status_code == 401
    assert service.get(
        "/v1/presentation/recommendation-list",
        headers={"X-API-Key": "view-key"},
    ).status_code == 422
    response = service.get(
        "/v1/presentation/recommendation-list?domain=crypto",
        headers={"X-API-Key": "view-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["domain_id"] == "crypto"
    assert body["domain_native_semantics"] is True
    assert body["universal_cross_domain_rank"] is False
    assert body["ordering_policy"] == "STABLE_ASSET_IDENTITY_NOT_NATIVE_RANK"
    assert body["rank_comparison_scope"] == "NATIVE_RANK_TYPE_ONLY"


def test_list_preserves_native_payload_and_missing_fields_without_synthesis():
    body = client().get(
        "/v1/presentation/recommendation-list?domain=crypto&query=Example",
        headers={"X-API-Key": "view-key"},
    ).json()
    item = body["items"][0]
    assert item["native_status"] == "watch"
    assert item["native_status_source_field"] == "native_recommendation"
    assert item["native_rank"] is None
    assert item["native_rank_type"] is None
    assert item["current_price_usd"] is None
    assert item["current_price_authority_available"] is False
    assert item["recommendation_payload"] == {"native_recommendation": "watch"}
    assert body["missing_fields_policy"] == "PRESERVE_MISSING"


def test_list_exposes_domain_native_filters_without_changing_ordering_contract():
    response = client().get(
        "/v1/presentation/recommendation-list"
        "?domain=mtg"
        "&native_status=BUY_CANDIDATE_NOW"
        "&native_rank_type=SECRET_LAIR_V1_1_PRODUCTION_COMPETITION_RANK"
        "&has_forecast=true"
        "&has_risk=false"
        "&current_price_authority_available=true"
        "&manual_execution_price_check_required=true",
        headers={"X-API-Key": "view-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filters"] == {
        "native_status": "BUY_CANDIDATE_NOW",
        "native_rank_type": "SECRET_LAIR_V1_1_PRODUCTION_COMPETITION_RANK",
        "has_forecast": True,
        "has_risk": False,
        "current_price_authority_available": True,
        "manual_execution_price_check_required": True,
    }
    assert body["ordering_policy"] == "STABLE_ASSET_IDENTITY_NOT_NATIVE_RANK"
    assert body["rank_comparison_scope"] == "NATIVE_RANK_TYPE_ONLY"
    assert body["universal_cross_domain_rank"] is False


def test_list_rejects_domain_not_present_in_active_certified_publication():
    response = client().get(
        "/v1/presentation/recommendation-list?domain=stocks",
        headers={"X-API-Key": "view-key"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOMAIN_NOT_IN_ACTIVE_PRESENTATION"


def test_production_list_contract_avoids_row_multiplication_rank_sorting_and_cross_domain_filters():
    source = (
        ROOT
        / "foundation"
        / "presentation"
        / "recommendation_list.py"
    ).read_text(encoding="utf-8")
    runtime = (ROOT / "scripts" / "run_production_api.py").read_text(encoding="utf-8")

    for marker in (
        "forecast_record_count",
        "risk_record_count",
        "native_purchase_status",
        "native_recommendation",
        "native_rank_type",
        "manual_execution_price_check_required",
        "current_price_authority_available",
        "has_forecast",
        "has_risk",
        "automatic_purchase_execution",
        '"universal_cross_domain_rank": False',
        '"ordering_policy": "STABLE_ASSET_IDENTITY_NOT_NATIVE_RANK"',
        '"rank_comparison_scope": "NATIVE_RANK_TYPE_ONLY"',
        '"missing_fields_policy": "PRESERVE_MISSING"',
    ):
        assert marker in source

    assert "SELECT COUNT(*)" in source
    assert "ORDER BY\n                    COALESCE(a.payload_json->>'asset_name', r.asset_id)" in source
    assert "ORDER BY r.payload_json->>'native_rank'" not in source
    assert 'app.get("/v1/presentation/recommendation-list")' in source
    assert "install_recommendation_list_routes" in runtime
