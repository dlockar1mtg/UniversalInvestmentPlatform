from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundation.presentation.recommendation_summary import (
    install_recommendation_summary_routes,
)


ROOT = Path(__file__).resolve().parents[2]


class FakeRecommendationSummaryRepository:
    def summary(self):
        return {
            "publication_id": "pub-1",
            "total_recommendations": 986,
            "domains": [
                {
                    "domain_id": "crypto",
                    "recommendation_count": 6,
                    "native_status_count": 6,
                    "native_statuses": {"watch": 5, "sell": 1},
                    "confidence_count": 6,
                    "native_rank_count": 0,
                    "native_rank_type_count": 0,
                    "native_rank_types": {},
                    "manual_price_check_required_count": 0,
                    "automatic_execution_count": 0,
                    "matched_asset_count": 6,
                    "certified_current_price_authority_count": 0,
                    "forecast_asset_count": 6,
                    "risk_asset_count": 6,
                    "identity_coverage": "6/6",
                    "forecast_coverage": "6/6",
                    "risk_coverage": "6/6",
                },
                {
                    "domain_id": "metals",
                    "recommendation_count": 12,
                    "native_status_count": 12,
                    "native_statuses": {"BUY": 6, "HOLD": 3},
                    "confidence_count": 12,
                    "native_rank_count": 0,
                    "native_rank_type_count": 0,
                    "native_rank_types": {},
                    "manual_price_check_required_count": 0,
                    "automatic_execution_count": 0,
                    "matched_asset_count": 12,
                    "certified_current_price_authority_count": 0,
                    "forecast_asset_count": 12,
                    "risk_asset_count": 11,
                    "identity_coverage": "12/12",
                    "forecast_coverage": "12/12",
                    "risk_coverage": "11/12",
                },
                {
                    "domain_id": "mtg",
                    "recommendation_count": 968,
                    "native_status_count": 968,
                    "native_statuses": {"BUY_CANDIDATE_NOW": 88},
                    "confidence_count": 0,
                    "native_rank_count": 931,
                    "native_rank_type_count": 931,
                    "native_rank_types": {
                        "COLLECTOR_FINAL_GOVERNED_RANK": 49,
                        "PRECOLLECTOR_PURCHASE_RANK": 95,
                        "SECRET_LAIR_V1_1_PRODUCTION_COMPETITION_RANK": 787,
                    },
                    "manual_price_check_required_count": 269,
                    "automatic_execution_count": 0,
                    "matched_asset_count": 968,
                    "certified_current_price_authority_count": 958,
                    "forecast_asset_count": 931,
                    "risk_asset_count": 0,
                    "identity_coverage": "968/968",
                    "forecast_coverage": "931/968",
                    "risk_coverage": "0/968",
                },
            ],
            "domain_native_semantics": True,
            "universal_cross_domain_rank": False,
            "automatic_execution": False,
            "missing_fields_policy": "PRESERVE_MISSING",
        }


def client():
    app = FastAPI()
    install_recommendation_summary_routes(
        app,
        {
            "viewer": ("view-key", ("viewer",)),
            "operator": ("operate-key", ("operator",)),
        },
        FakeRecommendationSummaryRepository(),
    )
    return TestClient(app)


def test_summary_endpoint_requires_read_permission_and_preserves_native_contract():
    service = client()
    assert service.get("/v1/presentation/recommendation-summary").status_code == 401
    response = service.get(
        "/v1/presentation/recommendation-summary",
        headers={"X-API-Key": "view-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_recommendations"] == 986
    assert body["domain_native_semantics"] is True
    assert body["universal_cross_domain_rank"] is False
    assert body["automatic_execution"] is False
    assert body["missing_fields_policy"] == "PRESERVE_MISSING"


def test_summary_contract_keeps_domain_status_and_rank_semantics_separate():
    body = client().get(
        "/v1/presentation/recommendation-summary",
        headers={"X-API-Key": "view-key"},
    ).json()
    domains = {item["domain_id"]: item for item in body["domains"]}
    assert domains["crypto"]["native_statuses"] == {"watch": 5, "sell": 1}
    assert domains["crypto"]["native_rank_types"] == {}
    assert domains["metals"]["native_rank_types"] == {}
    assert domains["mtg"]["native_statuses"]["BUY_CANDIDATE_NOW"] == 88
    assert domains["mtg"]["native_rank_types"]["COLLECTOR_FINAL_GOVERNED_RANK"] == 49
    assert domains["mtg"]["manual_price_check_required_count"] == 269


def test_summary_contract_exposes_coverage_without_synthesizing_missing_evidence():
    body = client().get(
        "/v1/presentation/recommendation-summary",
        headers={"X-API-Key": "view-key"},
    ).json()
    domains = {item["domain_id"]: item for item in body["domains"]}
    assert domains["crypto"]["identity_coverage"] == "6/6"
    assert domains["metals"]["risk_coverage"] == "11/12"
    assert domains["mtg"]["forecast_coverage"] == "931/968"
    assert domains["mtg"]["risk_coverage"] == "0/968"
    assert domains["crypto"]["certified_current_price_authority_count"] == 0
    assert domains["metals"]["certified_current_price_authority_count"] == 0
    assert domains["mtg"]["certified_current_price_authority_count"] == 958


def test_production_summary_source_has_required_fail_closed_guardrails():
    source = (
        ROOT
        / "foundation"
        / "presentation"
        / "recommendation_summary.py"
    ).read_text(encoding="utf-8")
    runtime = (ROOT / "scripts" / "run_production_api.py").read_text(encoding="utf-8")

    for marker in (
        "native_purchase_status",
        "native_recommendation",
        "manual_execution_price_check_required",
        "automatic_purchase_execution",
        "current_price_authority_available",
        "forecast_asset_count",
        "risk_asset_count",
        '"universal_cross_domain_rank": False',
        '"missing_fields_policy": "PRESERVE_MISSING"',
    ):
        assert marker in source

    assert 'app.get("/v1/presentation/recommendation-summary")' in source
    assert "install_recommendation_summary_routes" in runtime
