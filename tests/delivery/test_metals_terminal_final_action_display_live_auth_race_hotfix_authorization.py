import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config/metals/terminal_final_action_display_live_auth_race_hotfix_authorization.json"


def load_auth():
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_live_auth_race_hotfix_authorization_contract():
    obj = load_auth()
    assert obj["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-LIVE-AUTH-RACE-HOTFIX-AUTHORIZATION-1"
    assert obj["source_main_head"] == "d43993ca49f9494517374ae08d745706f65aac25"
    assert obj["live_failure"]["message"] == "Cannot set properties of null (setting 'innerHTML')"
    assert obj["diagnosis"]["recommendation_ui_replaces_recommendations_inner_html"] is True
    assert obj["diagnosis"]["dashboard_render_domain_cards_unconditionally_writes_removed_summary_node"] is True
    assert obj["diagnosis"]["stale_recommendations_hash_and_existing_session_key_can_trigger_concurrent_loads"] is True
    assert obj["diagnosis"]["failure_can_clear_valid_session_key_and_return_user_to_auth"] is True
    assert obj["diagnosis"]["metals_final_action_data_or_policy_defect"] is False
    assert sorted(obj["authorized_files"]) == sorted([
        "foundation/production/dashboard_assets/dashboard.js",
        "tests/delivery/test_rec_ui_1.py",
    ])
    assert all(obj["required_hotfix_behavior"].values())
    scope = obj["authorization_scope"]
    assert scope["fresh_main_based_hotfix_branch_creation_authorized"] is True
    assert scope["dashboard_js_hotfix_authorized"] is True
    assert scope["regression_test_change_authorized"] is True
    assert scope["local_test_execution_authorized"] is True
    assert scope["pull_request_creation_authorized_after_local_certification"] is False
    assert scope["main_merge_authorized"] is False
    assert scope["manual_render_deployment_authorized"] is False
    assert scope["hosted_database_write_authorized"] is False
    assert scope["analytical_database_write_authorized"] is False
    assert scope["read_api_change_authorized"] is False
    assert scope["recommendation_recompute_authorized"] is False
    assert scope["forecast_refresh_authorized"] is False
    assert scope["model_refresh_authorized"] is False
    assert scope["allocation_or_execution_authorized"] is False
    assert obj["authorization_decision"] == "AUTHORIZE_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_IMPLEMENTATION"
    assert obj["next_decision"] == "IMPLEMENT_AND_CERTIFY_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX"
