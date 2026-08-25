from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "config" / "metals" / "tactical_policy_v3_out_of_sequence_main_merge_recovery_review.json"

EXPECTED_ID = "METALS-TACTICAL-POLICY-V3-OUT-OF-SEQUENCE-MAIN-MERGE-RECOVERY-REVIEW-1"
EXPECTED_DECISION = "ACCEPT_TECHNICAL_MERGE_RESULT_AND_CLOSE_OUT_OF_SEQUENCE_GOVERNANCE_DISCREPANCY"
EXPECTED_NEXT = "DESIGN_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH"
EXPECTED_MERGE = "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"
EXPECTED_TREE = "216e79e61f2ec0ec58d91b99819464b2afe501c1"


def main() -> None:
    payload = json.loads(REVIEW.read_text(encoding="utf-8"))
    assert payload["review_id"] == EXPECTED_ID
    assert payload["pull_request_number"] == 60
    assert payload["merge_occurred_before_separate_merge_authorization"] is True
    assert payload["merge_commit_sha"] == EXPECTED_MERGE
    assert payload["post_merge_main_head"] == EXPECTED_MERGE
    assert payload["merge_tree_sha"] == EXPECTED_TREE
    assert payload["certified_deployment_tree_sha"] == EXPECTED_TREE
    assert payload["merge_tree_matches_certified_deployment_tree"] is True
    assert payload["merged_commit_count_from_deployment_package"] == 1
    assert payload["merged_runtime_file_count"] == 4
    assert payload["whole_research_branch_merged"] is False
    assert payload["post_merge_ci"]["universal_investment_platform_ci_conclusion"] == "success"
    assert payload["post_merge_ci"]["container_delivery_conclusion"] == "success"
    assert payload["technical_result"]["certified_bounded_runtime_package_reached_main"] is True
    assert payload["technical_result"]["rollback_required"] is False
    assert payload["technical_result"]["repeat_merge_required"] is False
    assert payload["technical_result"]["hosted_tactical_publication_reactivation_required"] is False
    assert payload["technical_result"]["analytical_database_rewrite_required"] is False
    assert payload["review_decision"] == EXPECTED_DECISION
    assert payload["boundaries"]["retroactive_merge_authorization_claimed"] is False
    for key, value in payload["boundaries"].items():
        assert value is False, key
    assert payload["next_decision"] == EXPECTED_NEXT

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "review_id": payload["review_id"],
        "pull_request_number": 60,
        "merge_commit_sha": EXPECTED_MERGE,
        "merge_tree_matches_certified_deployment_tree": True,
        "post_merge_ci_passed": True,
        "rollback_required": False,
        "review_decision": EXPECTED_DECISION,
        "next_decision": EXPECTED_NEXT,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
