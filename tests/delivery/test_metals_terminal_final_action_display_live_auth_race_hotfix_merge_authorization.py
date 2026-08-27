import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config/metals/terminal_final_action_display_live_auth_race_hotfix_merge_authorization.json"


def load_auth():
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_hotfix_merge_authorization_source_and_pr_contract_are_pinned():
    a = load_auth()
    assert a["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-LIVE-AUTH-RACE-HOTFIX-MERGE-AUTHORIZATION-1"
    assert a["source_governed_head"] == "676944480f92d9b21bffa94417fd144862c5d8d6"
    assert a["source_pull_request_number"] == 62
    assert a["source_main_base_sha"] == "d43993ca49f9494517374ae08d745706f65aac25"
    assert a["source_pull_request_head_sha"] == "47366660dd7e426c0dbed4ec262fdc8ac5736a39"
    assert a["source_pr_state"]["open"] is True
    assert a["source_pr_state"]["commit_count"] == 1
    assert a["source_pr_state"]["changed_file_count"] == 2
    assert a["source_pr_state"]["universal_investment_platform_ci_success"] is True
    assert a["source_pr_state"]["container_delivery_success"] is True


def test_hotfix_merge_authorization_scope_is_bounded():
    a = load_auth()
    scope = a["authorization_scope"]
    assert scope["pull_request_merge_authorized"] is True
    assert scope["main_merge_authorized"] is True
    assert scope["post_merge_main_verification_authorized"] is True
    assert scope["post_merge_ci_inspection_authorized"] is True
    assert scope["render_deployment_inspection_authorized"] is True
    for key in (
        "manual_render_deployment_authorized",
        "hotfix_branch_mutation_authorized",
        "additional_code_change_authorized",
        "hosted_database_write_authorized",
        "analytical_database_write_authorized",
        "read_api_change_authorized",
        "recommendation_recompute_authorized",
        "forecast_refresh_authorized",
        "model_refresh_authorized",
        "allocation_or_execution_authorized",
    ):
        assert scope[key] is False


def test_hotfix_merge_authorization_preserves_certified_behavior():
    a = load_auth()
    assert len(a["certified_behavior"]) == 7
    assert all(a["certified_behavior"].values())
    assert sorted(a["required_changed_files"]) == sorted([
        "foundation/production/dashboard_assets/dashboard.js",
        "tests/delivery/test_rec_ui_1.py",
    ])
    assert a["authorization_decision"] == "AUTHORIZE_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_MAIN_MERGE"
    assert a["next_decision"] == "MERGE_AND_CERTIFY_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_PR_62"
