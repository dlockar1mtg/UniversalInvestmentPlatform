import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "config/metals/tactical_policy_v3_bounded_main_deployment_package_review.json"

review = json.loads(REVIEW.read_text(encoding="utf-8"))
expected_files = [
    "foundation/production/http_service.py",
    "foundation/production/dashboard_assets/dashboard.html",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/recommendation_ui.js",
]

assert review["review_id"] == "METALS-TACTICAL-POLICY-V3-BOUNDED-MAIN-DEPLOYMENT-PACKAGE-REVIEW-1"
assert review["source_ui_integration_head"] == "a641adb46b422bb550bbbb89f3c781efd5463c00"
assert review["main_base_head"] == "10f4f4c0e3e96194314a46c058432dd6d04553d7"
assert review["deployment_branch"] == "deploy/metals-v3-tactical-ui"
assert review["deployment_head"] == "11c9f8909c63d42aee8b8a7324d172f551b17b37"
assert review["deployment_commit_count"] == 1
assert review["deployment_files"] == expected_files
assert all(review["runtime_changes"].values())
assert review["whole_research_branch_merge_authorized"] is False
assert review["main_deployment_authorized"] is False
assert review["pull_request_authorized"] is False
assert review["hosted_presentation_reactivation_authorized"] is False
assert review["analytical_database_write_authorized"] is False
assert review["second_metals_production_write_authorized"] is False
assert review["review_decision"] == "BOUNDED_PACKAGE_CONSTRUCTED_REQUIRES_LOCAL_REGRESSION_CERTIFICATION_BEFORE_PR"
assert review["next_decision"] == "CERTIFY_METALS_V3_BOUNDED_MAIN_DEPLOYMENT_PACKAGE"

print(json.dumps({
    "status": "PASS",
    "read_only": True,
    "review_id": review["review_id"],
    "deployment_branch": review["deployment_branch"],
    "deployment_head": review["deployment_head"],
    "main_base_head": review["main_base_head"],
    "deployment_commit_count": review["deployment_commit_count"],
    "deployment_file_count": len(review["deployment_files"]),
    "main_deployment_authorized": review["main_deployment_authorized"],
    "pull_request_authorized": review["pull_request_authorized"],
    "whole_research_branch_merge_authorized": review["whole_research_branch_merge_authorized"],
    "next_decision": review["next_decision"],
}, indent=2, sort_keys=True))
