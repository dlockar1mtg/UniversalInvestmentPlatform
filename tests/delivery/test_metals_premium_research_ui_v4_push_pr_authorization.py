from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "premium_research_ui_v4_push_pr_authorization.json"


def load_auth() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_identity_and_local_commit_are_bound() -> None:
    data = load_auth()
    assert data["authorization_id"] == "METALS-PREMIUM-RESEARCH-UI-V4-PUSH-PR-AUTHORIZATION-1"
    assert data["production_base"] == "348f2a94c4bea371bde47dac880dc1d91fe7fa07"
    assert data["local_reconciliation_head"] == "1d453a38e8ca63e4b76e2d3e391106c5c4eec26e"
    assert data["local_reconciliation_parent"] == data["production_base"]
    assert len(data["committed_files"]) == 2


def test_push_pr_open_but_merge_closed() -> None:
    scope = load_auth()["authorization_scope"]
    assert scope["deployment_branch_push_authorized"] is True
    assert scope["pull_request_creation_authorized"] is True
    assert scope["pull_request_review_authorized"] is True
    assert scope["merge_authorized"] is False
    for key in (
        "additional_code_change_authorized",
        "hosted_presentation_mutation_authorized",
        "analytical_database_write_authorized",
        "model_refresh_authorized",
        "forecast_refresh_authorized",
        "recommendation_recompute_authorized",
        "manual_render_deployment_authorized",
    ):
        assert scope[key] is False


def test_certified_semantics_are_preserved() -> None:
    cert = load_auth()["certification"]
    assert cert["rec_ui_tests_passed"] == 16
    assert cert["status_filter_controls_labeled"] == 3
    assert cert["final_action_first_preserved"] is True
    assert cert["premium_metals_ui_preserved"] is True
    assert cert["crypto_semantics_preserved"] is True
    assert cert["mtg_native_semantics_preserved"] is True
    assert cert["dom_ownership_safeguard_preserved"] is True
    assert cert["exact_two_file_boundary"] is True
