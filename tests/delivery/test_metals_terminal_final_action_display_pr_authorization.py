import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "terminal_final_action_display_pr_authorization.json"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_pr_authorization_binds_exact_deployment_package():
    payload = load()
    assert payload["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-PR-AUTHORIZATION-1"
    assert payload["source_deployment_head"] == "23a0719c8bf6bc26ca7cc8c24b48c3ef581b8c18"
    assert payload["main_base_head"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"
    assert payload["deployment_compare"] == {
        "status": "ahead",
        "ahead_by": 1,
        "behind_by": 0,
        "total_commits": 1,
    }
    assert payload["authorized_pr"]["base"] == "main"
    assert payload["authorized_pr"]["head"] == "deploy/metals-final-action-display-fix"
    assert payload["authorized_pr"]["required_commit_count"] == 1
    assert payload["authorized_pr"]["required_changed_files"] == [
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "tests/delivery/test_rec_ui_1.py",
    ]


def test_pr_authorization_opens_only_pr_creation_review_and_check_inspection():
    scope = load()["authorization_scope"]
    assert {k for k, v in scope.items() if v is True} == {
        "pull_request_creation_authorized",
        "pull_request_review_authorized",
        "pull_request_check_inspection_authorized",
    }
    assert scope["main_merge_authorized"] is False
    assert scope["render_deployment_authorized"] is False
    assert scope["deployment_branch_mutation_authorized"] is False
    assert scope["additional_code_change_authorized"] is False


def test_pr_authorization_requires_separate_merge_and_render_gates():
    payload = load()
    assert all(payload["required_pr_behavior"].values())
    assert payload["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR_CREATION"
    assert payload["next_decision"] == "CREATE_AND_CERTIFY_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR"
