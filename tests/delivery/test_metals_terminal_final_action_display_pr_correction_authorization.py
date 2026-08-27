from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "terminal_final_action_display_pr_correction_authorization.json"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_pr_correction_authorization_is_bound_to_existing_pr_and_deployment_head():
    doc = load()
    assert doc["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-PR-CORRECTION-AUTHORIZATION-1"
    assert doc["source_pull_request_number"] == 61
    assert doc["source_pull_request_base"] == "main"
    assert doc["source_pull_request_head"] == "deploy/metals-final-action-display-fix"
    assert doc["source_pull_request_head_sha"] == "23a0719c8bf6bc26ca7cc8c24b48c3ef581b8c18"


def test_pr_correction_authorizes_only_two_existing_deployment_files():
    doc = load()
    assert set(doc["authorized_files"]) == {
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "tests/delivery/test_rec_ui_1.py",
    }


def test_pr_correction_requires_truthful_metals_labels_and_preserved_native_evidence():
    behavior = load()["required_correction_behavior"]
    assert behavior["metals_primary_visible_decision_remains_final_action_first"] is True
    assert behavior["metals_detail_primary_label_must_identify_governed_final_decision"] is True
    assert behavior["preserved_native_recommendation_must_remain_separately_visible_for_metals"] is True
    assert behavior["metals_status_filter_copy_must_not_describe_final_action_values_as_native"] is True
    assert behavior["crypto_native_recommendation_semantics_preserved"] is True
    assert behavior["mtg_native_purchase_status_semantics_preserved"] is True


def test_pr_correction_keeps_merge_and_deploy_closed():
    scope = load()["authorization_scope"]
    assert scope["deployment_branch_ui_copy_correction_authorized"] is True
    assert scope["deployment_branch_test_correction_authorized"] is True
    assert scope["pull_request_update_by_existing_head_commit_authorized"] is True
    assert scope["main_merge_authorized"] is False
    assert scope["render_deployment_authorized"] is False
    assert scope["hosted_database_write_authorized"] is False
    assert scope["analytical_database_write_authorized"] is False
    assert scope["read_api_change_authorized"] is False


def test_pr_correction_decision_and_next_step_are_exact():
    doc = load()
    assert doc["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR_LABEL_CORRECTION"
    assert doc["next_decision"] == "IMPLEMENT_AND_CERTIFY_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR_LABEL_CORRECTION"
