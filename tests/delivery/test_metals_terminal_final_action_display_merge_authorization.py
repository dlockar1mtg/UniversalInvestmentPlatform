from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "terminal_final_action_display_merge_authorization.json"


def load_auth():
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_merge_authorization_is_bound_to_final_pr_state():
    auth = load_auth()
    assert auth["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-MERGE-AUTHORIZATION-1"
    assert auth["source_pull_request_number"] == 61
    assert auth["source_pull_request_base"] == "main"
    assert auth["source_pull_request_head"] == "deploy/metals-final-action-display-fix"
    assert auth["source_pull_request_head_sha"] == "29a428de098977661421d9350436f1ffa6596d62"
    assert auth["source_main_base_sha"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"
    assert auth["source_pr_state"]["open"] is True
    assert auth["source_pr_state"]["mergeable"] is True
    assert auth["source_pr_state"]["commit_count"] == 3
    assert auth["source_pr_state"]["changed_file_count"] == 2
    assert auth["source_pr_state"]["universal_investment_platform_ci_success"] is True
    assert auth["source_pr_state"]["container_delivery_success"] is True


def test_merge_scope_is_narrow_and_expected_head_is_pinned():
    auth = load_auth()
    scope = auth["authorization_scope"]
    assert scope["main_merge_authorized"] is True
    assert scope["pull_request_merge_authorized"] is True
    assert scope["post_merge_main_verification_authorized"] is True
    assert scope["post_merge_ci_inspection_authorized"] is True
    assert scope["render_deployment_inspection_authorized"] is True
    assert scope["manual_render_deployment_authorized"] is False
    assert scope["deployment_branch_mutation_authorized"] is False
    assert scope["additional_code_change_authorized"] is False
    assert scope["hosted_database_write_authorized"] is False
    assert scope["analytical_database_write_authorized"] is False
    assert scope["read_api_change_authorized"] is False
    assert scope["recommendation_recompute_authorized"] is False
    assert scope["forecast_refresh_authorized"] is False
    assert scope["model_refresh_authorized"] is False
    assert scope["allocation_or_execution_authorized"] is False
    contract = auth["merge_contract"]
    assert contract["required_expected_head_sha"] == auth["source_pull_request_head_sha"]
    assert contract["merge_only_if_head_unchanged"] is True
    assert contract["merge_only_if_main_base_unchanged"] is True


def test_final_semantics_are_certified_for_merge():
    semantics = load_auth()["certified_semantics"]
    assert semantics["metals_display_precedence"] == "FINAL_ACTION_THEN_RECOMMENDATION_THEN_NATIVE_RECOMMENDATION"
    assert semantics["metals_final_decision_primary"] is True
    assert semantics["metals_native_recommendation_supporting_evidence"] is True
    assert semantics["metals_forecast_risk_supporting_evidence"] is True
    assert semantics["metals_tactical_state_separate_timing_context"] is True
    assert semantics["metals_decision_status_copy"] is True
    assert semantics["crypto_native_semantics_preserved"] is True
    assert semantics["mtg_native_purchase_status_preserved"] is True
