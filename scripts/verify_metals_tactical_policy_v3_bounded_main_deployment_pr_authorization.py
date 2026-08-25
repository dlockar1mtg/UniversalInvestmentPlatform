from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_bounded_main_deployment_pr_authorization.json"

EXPECTED_FILES = [
    "foundation/production/dashboard_assets/dashboard.html",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/http_service.py",
]


def main() -> None:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-BOUNDED-MAIN-DEPLOYMENT-PR-AUTHORIZATION-1"
    assert auth["source_package_review_id"] == "METALS-TACTICAL-POLICY-V3-BOUNDED-MAIN-DEPLOYMENT-PACKAGE-REVIEW-1"
    assert auth["source_package_review_head"] == "4e662944b3f016306dff295be81688996dec737a"
    assert auth["source_package_certification_status"] == "PASS"
    assert auth["main_base_head"] == "10f4f4c0e3e96194314a46c058432dd6d04553d7"
    assert auth["deployment_branch"] == "deploy/metals-v3-tactical-ui"
    assert auth["deployment_head"] == "11c9f8909c63d42aee8b8a7324d172f551b17b37"
    assert auth["deployment_commit_count"] == 1
    assert auth["deployment_file_count"] == 4
    assert sorted(auth["deployment_files"]) == sorted(EXPECTED_FILES)

    regression = auth["local_regression_certification"]
    assert regression["rec_ui_tests_passed"] == 10
    assert regression["production_tests_passed"] == 166
    assert regression["all_runtime_files_exactly_match_certified_metals_source"] is True
    assert regression["research_worktree_clean"] is True
    assert regression["disposable_certification_worktree_removed"] is True
    assert regression["analytical_database_unchanged"] is True

    assert auth["authorization_decision"] == "AUTHORIZE_OPEN_AND_REVIEW_BOUNDED_METALS_V3_MAIN_DEPLOYMENT_PR"
    action = auth["authorized_action"]
    assert action["open_pull_request"] is True
    assert action["base_branch"] == "main"
    assert action["head_branch"] == "deploy/metals-v3-tactical-ui"
    assert action["inspect_exact_pr_diff"] is True
    assert action["inspect_ci_checks"] is True

    assert all(value is False for value in auth["boundaries"].values())
    assert all(value is True for value in auth["required_pr_review"].values())
    assert auth["next_decision"] == "OPEN_AND_REVIEW_METALS_V3_BOUNDED_MAIN_DEPLOYMENT_PR"

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "authorization_decision": auth["authorization_decision"],
        "main_base_head": auth["main_base_head"],
        "deployment_branch": auth["deployment_branch"],
        "deployment_head": auth["deployment_head"],
        "deployment_commit_count": auth["deployment_commit_count"],
        "deployment_file_count": auth["deployment_file_count"],
        "pull_request_authorized": True,
        "merge_authorized": False,
        "whole_research_branch_merge_authorized": False,
        "next_decision": auth["next_decision"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
