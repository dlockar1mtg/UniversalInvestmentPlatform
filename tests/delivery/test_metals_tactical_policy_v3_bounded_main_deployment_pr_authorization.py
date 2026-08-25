from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_bounded_main_deployment_pr_authorization.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_bounded_main_deployment_pr_authorization.py"

EXPECTED_FILES = {
    "foundation/production/dashboard_assets/dashboard.html",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/http_service.py",
}


def load_auth() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_authorization_is_bound_to_certified_package() -> None:
    auth = load_auth()
    assert auth["source_package_review_head"] == "4e662944b3f016306dff295be81688996dec737a"
    assert auth["main_base_head"] == "10f4f4c0e3e96194314a46c058432dd6d04553d7"
    assert auth["deployment_branch"] == "deploy/metals-v3-tactical-ui"
    assert auth["deployment_head"] == "11c9f8909c63d42aee8b8a7324d172f551b17b37"
    assert auth["deployment_commit_count"] == 1
    assert auth["deployment_file_count"] == 4
    assert set(auth["deployment_files"]) == EXPECTED_FILES


def test_authorization_allows_pr_review_not_merge() -> None:
    auth = load_auth()
    assert auth["authorization_decision"] == "AUTHORIZE_OPEN_AND_REVIEW_BOUNDED_METALS_V3_MAIN_DEPLOYMENT_PR"
    assert auth["authorized_action"]["open_pull_request"] is True
    assert auth["authorized_action"]["inspect_exact_pr_diff"] is True
    assert auth["authorized_action"]["inspect_ci_checks"] is True
    assert auth["boundaries"]["merge_authorized"] is False
    assert auth["boundaries"]["main_direct_push_authorized"] is False
    assert auth["boundaries"]["whole_research_branch_merge_authorized"] is False
    assert auth["boundaries"]["render_deployment_certified"] is False


def test_regression_authority_is_preserved() -> None:
    auth = load_auth()
    regression = auth["local_regression_certification"]
    assert regression["rec_ui_tests_passed"] == 10
    assert regression["production_tests_passed"] == 166
    assert regression["all_runtime_files_exactly_match_certified_metals_source"] is True
    assert regression["analytical_database_unchanged"] is True


def test_pr_review_is_fail_closed() -> None:
    auth = load_auth()
    review = auth["required_pr_review"]
    assert all(review.values())
    assert auth["next_decision"] == "OPEN_AND_REVIEW_METALS_V3_BOUNDED_MAIN_DEPLOYMENT_PR"


def test_verifier_is_static_and_read_only() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    assert "read_only" in source
    assert "create_pull_request" not in source
    assert "merge" not in source.lower() or '"merge_authorized": False' in source
