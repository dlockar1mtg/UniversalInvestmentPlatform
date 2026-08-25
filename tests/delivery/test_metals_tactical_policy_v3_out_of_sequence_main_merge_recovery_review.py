from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "config" / "metals" / "tactical_policy_v3_out_of_sequence_main_merge_recovery_review.json"


def load_review() -> dict:
    return json.loads(REVIEW.read_text(encoding="utf-8"))


def test_recovery_review_closes_only_the_governance_discrepancy() -> None:
    review = load_review()
    assert review["review_id"] == "METALS-TACTICAL-POLICY-V3-OUT-OF-SEQUENCE-MAIN-MERGE-RECOVERY-REVIEW-1"
    assert review["merge_occurred_before_separate_merge_authorization"] is True
    assert review["boundaries"]["retroactive_merge_authorization_claimed"] is False
    assert review["review_decision"] == "ACCEPT_TECHNICAL_MERGE_RESULT_AND_CLOSE_OUT_OF_SEQUENCE_GOVERNANCE_DISCREPANCY"


def test_exact_certified_runtime_package_reached_main() -> None:
    review = load_review()
    assert review["merge_commit_sha"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"
    assert review["post_merge_main_head"] == review["merge_commit_sha"]
    assert review["merge_tree_sha"] == "216e79e61f2ec0ec58d91b99819464b2afe501c1"
    assert review["merge_tree_sha"] == review["certified_deployment_tree_sha"]
    assert review["merge_tree_matches_certified_deployment_tree"] is True
    assert review["merged_commit_count_from_deployment_package"] == 1
    assert review["merged_runtime_file_count"] == 4
    assert review["whole_research_branch_merged"] is False


def test_post_merge_ci_passed_and_no_reexecution_is_needed() -> None:
    review = load_review()
    assert review["post_merge_ci"]["universal_investment_platform_ci_conclusion"] == "success"
    assert review["post_merge_ci"]["container_delivery_conclusion"] == "success"
    assert review["technical_result"]["rollback_required"] is False
    assert review["technical_result"]["repeat_merge_required"] is False
    assert review["technical_result"]["hosted_tactical_publication_reactivation_required"] is False
    assert review["technical_result"]["analytical_database_rewrite_required"] is False


def test_no_new_downstream_authority_is_created() -> None:
    review = load_review()
    for key, value in review["boundaries"].items():
        assert value is False, key
    assert review["next_decision"] == "DESIGN_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH"
