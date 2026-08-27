import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config/metals/terminal_final_action_display_live_auth_race_hotfix_pr_authorization.json"


def load_auth():
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_live_auth_race_hotfix_pr_authorization_binds_certified_branch():
    data = load_auth()
    assert data["source_main_head"] == "d43993ca49f9494517374ae08d745706f65aac25"
    assert data["source_hotfix_branch"] == "hotfix/metals-recommendations-auth-race"
    assert data["source_hotfix_head"] == "47366660dd7e426c0dbed4ec262fdc8ac5736a39"
    assert data["hotfix_state"]["ahead_by"] == 1
    assert data["hotfix_state"]["behind_by"] == 0
    assert data["hotfix_state"]["commit_count"] == 1
    assert data["hotfix_state"]["changed_file_count"] == 2
    assert data["hotfix_state"]["local_rec_ui_tests_passed"] == 14
    assert data["hotfix_state"]["git_diff_check_passed"] is True


def test_live_auth_race_hotfix_pr_authorization_has_exact_two_file_contract():
    data = load_auth()
    assert sorted(data["authorized_pr"]["required_changed_files"]) == [
        "foundation/production/dashboard_assets/dashboard.js",
        "tests/delivery/test_rec_ui_1.py",
    ]
    assert data["authorized_pr"]["base"] == "main"
    assert data["authorized_pr"]["head"] == "hotfix/metals-recommendations-auth-race"
    assert data["authorized_pr"]["required_expected_head_sha"] == "47366660dd7e426c0dbed4ec262fdc8ac5736a39"
    assert data["authorized_pr"]["required_commit_count"] == 1


def test_live_auth_race_hotfix_pr_authorization_preserves_semantics_and_closes_merge():
    data = load_auth()
    assert all(data["certified_behavior"].values())
    scope = data["authorization_scope"]
    assert scope["pull_request_creation_authorized"] is True
    assert scope["pull_request_review_authorized"] is True
    assert scope["pull_request_check_inspection_authorized"] is True
    for key in (
        "main_merge_authorized",
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
    assert data["authorization_decision"] == "AUTHORIZE_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_PULL_REQUEST_CREATION"
    assert data["next_decision"] == "CREATE_AND_CERTIFY_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_PULL_REQUEST"
