from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "premium_research_ui_pr_authorization.json"


def load_auth() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_pr_authorization_identity_and_heads_are_bound() -> None:
    data = load_auth()
    assert data["authorization_id"] == "METALS-PREMIUM-RESEARCH-UI-PR-AUTHORIZATION-1"
    assert data["source_governed_head"] == "b4c13cf3c2bac22f23bfd0934d22a3e820eaaade"
    assert data["implementation_head"] == "8581dbbc1a9545afa72cf1c622831e7fab052686"
    assert data["expected_main_head"] == "348f2a94c4bea371bde47dac880dc1d91fe7fa07"


def test_pr_authorization_scope_opens_pr_only() -> None:
    scope = load_auth()["authorization_scope"]
    assert scope["pull_request_creation_authorized"] is True
    assert scope["pull_request_review_authorized"] is True
    assert scope["merge_authorized"] is False
    for key in (
        "repository_additional_code_change_authorized",
        "hosted_presentation_mutation_authorized",
        "analytical_database_write_authorized",
        "model_refresh_authorized",
        "forecast_refresh_authorized",
        "recommendation_recompute_authorized",
        "manual_render_deployment_authorized",
    ):
        assert scope[key] is False


def test_pr_authorization_semantic_contract_is_preserved() -> None:
    contract = load_auth()["implementation_contract"]
    assert contract["commit_count"] == 1
    assert sorted(contract["changed_files"]) == sorted([
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "tests/delivery/test_rec_ui_1.py",
    ])
    assert contract["delivery_test_count"] == 13
    assert contract["implementation_authorization_test_count"] == 3
    assert contract["final_action_remains_primary"] is True
    assert contract["native_recommendation_remains_supporting"] is True
    assert contract["tactical_context_remains_supporting"] is True
    assert contract["bil_remains_reference_control"] is True
    assert contract["metals_forecast_horizons_months"] == [3, 6, 12, 24]
    assert contract["missing_forecast_authority_remains_explicit"] is True
    assert contract["crypto_contract_preserved"] is True
    assert contract["mtg_contract_preserved"] is True
