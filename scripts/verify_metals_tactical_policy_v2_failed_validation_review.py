from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_failed_validation_review.json"


def main() -> int:
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    if review.get("review_id") != "METALS-TACTICAL-POLICY-V2-FAILED-VALIDATION-REVIEW-1":
        raise RuntimeError("unexpected failed-validation review")
    if review.get("source_evaluation") != "METALS-TACTICAL-POLICY-V2-VALIDATION-EVALUATION-1":
        raise RuntimeError("unexpected source evaluation")
    if review.get("evaluation_result") != "FAIL":
        raise RuntimeError("V2 result is not preserved as FAIL")
    if review.get("evaluation_artifact_sha256") != "70b8d0fb10e2debbf205548b66d82b16fedba446a690036ba8355f7c842b5a53":
        raise RuntimeError("evaluation artifact hash changed")

    support = review["observed_support"]
    if int(support["constructive_63d_observations"]) != 489:
        raise RuntimeError("constructive support changed")
    if int(support["defensive_63d_observations"]) != 639:
        raise RuntimeError("defensive support changed")
    if int(support["minimum_required_per_compared_group"]) != 20:
        raise RuntimeError("minimum support changed")
    if support["support_requirement_met"] is not True:
        raise RuntimeError("support requirement must remain met")

    checks = review["governed_check_results"]
    for key in (
        "constructive_63d_median_return_gt_defensive",
        "constructive_63d_positive_return_rate_gt_defensive",
        "defensive_63d_mean_mae_more_negative_than_constructive",
    ):
        if checks[key] is not False:
            raise RuntimeError(f"failed directional check changed: {key}")
    for key in (
        "holdout_posture_change_rate_lte_0_50",
        "minimum_group_support_met",
        "no_semantic_or_governance_violation",
    ):
        if checks[key] is not True:
            raise RuntimeError(f"passing governance/support check changed: {key}")

    findings = review["review_findings"]
    required_true = (
        "v2_failure_is_conclusive_under_locked_rules",
        "failure_is_not_due_to_insufficient_group_support",
        "directional_relationship_is_opposite_locked_tactical_semantics",
        "constructive_group_had_lower_63d_median_return_than_defensive",
        "constructive_group_had_lower_63d_positive_return_rate_than_defensive",
        "constructive_group_had_more_negative_63d_mean_mae_than_defensive",
        "posture_churn_gate_passed",
        "no_governance_violation_detected",
        "v2_candidate_may_not_be_authorized_for_live_tactical_posture",
        "consumed_validation_interval_may_not_be_reused_as_unseen_evidence",
    )
    for key in required_true:
        if findings[key] is not True:
            raise RuntimeError(f"required finding changed: {key}")

    controls = review["controls"]
    if controls["failed_validation_review_authorized"] is not True:
        raise RuntimeError("review is not authorized")
    for key, value in controls.items():
        if key == "failed_validation_review_authorized":
            continue
        if value is not False:
            raise RuntimeError(f"prohibited authority changed: {key}")

    if review.get("next_decision") != "AUTHORIZE_METALS_TACTICAL_POLICY_V3_RESEARCH_DESIGN":
        raise RuntimeError("unexpected next decision")

    output = {
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "source_evaluation": review["source_evaluation"],
        "evaluation_result": review["evaluation_result"],
        "evaluation_artifact_sha256": review["evaluation_artifact_sha256"],
        "constructive_63d_observations": support["constructive_63d_observations"],
        "defensive_63d_observations": support["defensive_63d_observations"],
        "minimum_group_support": support["minimum_required_per_compared_group"],
        "support_requirement_met": support["support_requirement_met"],
        "directional_check_failures": 3,
        "posture_churn_gate_passed": findings["posture_churn_gate_passed"],
        "validation_interval_consumed": review["validation_interval"]["consumed"],
        "v2_live_use_authorized": controls["v2_candidate_live_use_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "v3_research_design_authorized": controls["v3_research_design_authorized"],
        "production_database_write_executed": False,
        "native_source_query_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": controls["cross_domain_rank_authorized"],
        "allocation_policy_authorized": controls["allocation_policy_authorized"],
        "automatic_execution_authorized": controls["automatic_execution_authorized"],
        "next_decision": review["next_decision"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
