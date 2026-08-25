import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_review_pins_exact_bounded_deployment_lineage():
    review = json.loads(read("config/metals/tactical_policy_v3_bounded_main_deployment_package_review.json"))
    assert review["source_ui_integration_head"] == "a641adb46b422bb550bbbb89f3c781efd5463c00"
    assert review["main_base_head"] == "10f4f4c0e3e96194314a46c058432dd6d04553d7"
    assert review["deployment_branch"] == "deploy/metals-v3-tactical-ui"
    assert review["deployment_head"] == "11c9f8909c63d42aee8b8a7324d172f551b17b37"
    assert review["deployment_commit_count"] == 1


def test_review_allows_only_four_runtime_files():
    review = json.loads(read("config/metals/tactical_policy_v3_bounded_main_deployment_package_review.json"))
    assert review["deployment_files"] == [
        "foundation/production/http_service.py",
        "foundation/production/dashboard_assets/dashboard.html",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/recommendation_ui.js",
    ]
    assert all(review["runtime_changes"].values())


def test_deployment_remains_unconsumed_and_unmerged_pending_certification():
    review = json.loads(read("config/metals/tactical_policy_v3_bounded_main_deployment_package_review.json"))
    assert review["whole_research_branch_merge_authorized"] is False
    assert review["main_deployment_authorized"] is False
    assert review["pull_request_authorized"] is False
    assert review["hosted_presentation_reactivation_authorized"] is False
    assert review["analytical_database_write_authorized"] is False
    assert review["second_metals_production_write_authorized"] is False
    assert review["review_decision"] == "BOUNDED_PACKAGE_CONSTRUCTED_REQUIRES_LOCAL_REGRESSION_CERTIFICATION_BEFORE_PR"
    assert review["next_decision"] == "CERTIFY_METALS_V3_BOUNDED_MAIN_DEPLOYMENT_PACKAGE"
