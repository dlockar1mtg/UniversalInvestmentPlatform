from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def read_review():
    return json.loads(
        (ROOT / "config/metals/terminal_final_action_display_deployment_package_review.json")
        .read_text(encoding="utf-8")
    )


def test_review_rejects_whole_research_branch_deployment():
    document = read_review()
    compare = document["research_to_main_compare"]
    constraints = document["package_constraints"]
    assert compare["status"] == "diverged"
    assert compare["research_ahead_by"] == 442
    assert compare["research_behind_by"] == 2
    assert compare["whole_research_branch_merge_safe"] is False
    assert compare["direct_research_branch_pr_safe"] is False
    assert constraints["whole_research_branch_merge_authorized"] is False
    assert constraints["direct_research_branch_pr_authorized"] is False
    assert constraints["cherry_pick_entire_implementation_commit_authorized"] is False


def test_review_requires_fresh_main_based_two_file_package():
    document = read_review()
    assert document["deployment_strategy"] == "RECONSTRUCT_EXACT_DISPLAY_SEMANTIC_FIX_ON_FRESH_BRANCH_FROM_CURRENT_MAIN"
    assert document["deployment_branch"] == "deploy/metals-final-action-display-fix"
    assert set(document["deployment_package_files"]) == {
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "tests/delivery/test_rec_ui_1.py",
    }
    constraints = document["package_constraints"]
    assert constraints["fresh_main_based_deployment_branch_required"] is True
    assert constraints["exact_two_file_package_required"] is True
    assert constraints["local_regression_certification_required_before_pr"] is True
    assert constraints["pull_request_authorized"] is False
    assert constraints["main_merge_authorized"] is False
    assert constraints["render_deployment_authorized"] is False


def test_review_preserves_domain_semantics_and_non_deployment_boundaries():
    semantics = read_review()["deployment_semantics"]
    assert semantics["metals_display_priority"] == "final_action_then_recommendation_then_native_recommendation"
    assert semantics["crypto_native_status_semantics_preserved"] is True
    assert semantics["mtg_native_purchase_status_semantics_preserved"] is True
    assert semantics["search_and_status_filter_use_display_status"] is True
    assert semantics["bil_reference_control_visible"] is True
    assert semantics["hosted_payload_change_required"] is False
    assert semantics["read_api_change_required"] is False
    assert semantics["analytical_change_required"] is False


def test_review_next_step_is_package_construction_not_pr():
    document = read_review()
    assert document["review_decision"] == "BOUNDED_MAIN_BASED_DEPLOYMENT_PACKAGE_REQUIRED_BEFORE_PR_AUTHORIZATION"
    assert document["next_decision"] == "CONSTRUCT_AND_CERTIFY_BOUNDED_METALS_TERMINAL_FINAL_ACTION_DISPLAY_DEPLOYMENT_PACKAGE"
