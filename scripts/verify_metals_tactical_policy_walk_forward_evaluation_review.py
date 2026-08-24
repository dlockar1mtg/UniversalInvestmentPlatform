from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_walk_forward_evaluation_review.json"


def main() -> int:
    review = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    if review.get("review_id") != "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-REVIEW-1":
        raise RuntimeError("unexpected tactical evaluation review")
    if review.get("source_evaluation") != "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-1":
        raise RuntimeError("unexpected tactical evaluation source")
    if review.get("review_status") != "INCONCLUSIVE_NOT_AUTHORIZED":
        raise RuntimeError("candidate v1 review status changed")

    observed = review.get("observed_holdout") or {}
    if int(observed.get("constructive_observation_count", -1)) != 280:
        raise RuntimeError("constructive holdout support changed")
    if int(observed.get("defensive_observation_count", -1)) != 15:
        raise RuntimeError("defensive holdout support changed")
    if int(observed.get("minimum_supported_observations_per_compared_group", -1)) != 20:
        raise RuntimeError("minimum support rule changed")
    if observed.get("minimum_group_support_met") is not False:
        raise RuntimeError("minimum support result changed")
    if float(observed.get("constructive_63d_median_return_pct")) <= float(observed.get("defensive_63d_median_return_pct")):
        raise RuntimeError("observed return separation no longer reconciles")
    if float(observed.get("constructive_63d_positive_return_rate")) <= float(observed.get("defensive_63d_positive_return_rate")):
        raise RuntimeError("observed positive-rate separation no longer reconciles")
    if float(observed.get("defensive_63d_mean_maximum_adverse_excursion_pct")) >= float(observed.get("constructive_63d_mean_maximum_adverse_excursion_pct")):
        raise RuntimeError("observed defensive adverse excursion no longer reconciles")
    if float(observed.get("holdout_posture_change_rate")) > 0.50:
        raise RuntimeError("observed holdout churn exceeds locked limit")

    findings = review.get("review_findings") or {}
    for key in (
        "candidate_version_1_may_not_be_declared_pass",
        "candidate_version_1_may_not_be_declared_fail_due_to_locked_inconclusive_rule",
        "constructive_vs_defensive_return_separation_is_directionally_favorable_but_not_validated",
        "constructive_vs_defensive_positive_rate_separation_is_directionally_favorable_but_not_validated",
        "defensive_group_support_is_insufficient",
        "defensive_group_showed_more_adverse_excursion_than_constructive",
        "original_mae_pass_rule_is_semantically_misaligned_with_a_defensive_risk_signal",
        "observed_holdout_results_are_now_consumed_and_may_not_be_reused_as_unseen_validation_for_a_revised_candidate",
    ):
        if findings.get(key) is not True:
            raise RuntimeError(f"required review finding changed: {key}")

    next_cycle = review.get("required_next_cycle_constraints") or {}
    for key in (
        "new_candidate_version_required_for_any_rule_change",
        "candidate_v1_thresholds_may_not_be_rewritten",
        "new_validation_authority_required_before_any_live_tactical_posture",
        "revised_mae_interpretation_must_be_pre_specified_before_new_outcome_evaluation",
        "defensive_support_problem_must_be_addressed_without_relaxing_support_after_the_fact",
        "previously_observed_holdout_may_be_used_for_research_diagnostics_only",
        "new_unseen_validation_evidence_required_for_production_authorization",
    ):
        if next_cycle.get(key) is not True:
            raise RuntimeError(f"required next-cycle constraint changed: {key}")

    controls = review.get("controls") or {}
    if controls.get("evaluation_review_authorized") is not True:
        raise RuntimeError("evaluation review is not authorized")
    if controls.get("candidate_v1_inconclusive_certified") is not True:
        raise RuntimeError("candidate v1 inconclusive result is not certified")
    for key in (
        "candidate_v1_pass_authorized",
        "candidate_v1_fail_authorized",
        "candidate_threshold_change_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited review control changed: {key}")

    result = {
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "source_evaluation": review["source_evaluation"],
        "candidate_v1_result": "INCONCLUSIVE",
        "constructive_holdout_observations": observed["constructive_observation_count"],
        "defensive_holdout_observations": observed["defensive_observation_count"],
        "minimum_supported_observations_per_compared_group": observed["minimum_supported_observations_per_compared_group"],
        "minimum_group_support_met": observed["minimum_group_support_met"],
        "constructive_63d_median_return_pct": observed["constructive_63d_median_return_pct"],
        "defensive_63d_median_return_pct": observed["defensive_63d_median_return_pct"],
        "constructive_63d_positive_return_rate": observed["constructive_63d_positive_return_rate"],
        "defensive_63d_positive_return_rate": observed["defensive_63d_positive_return_rate"],
        "constructive_63d_mean_mae_pct": observed["constructive_63d_mean_maximum_adverse_excursion_pct"],
        "defensive_63d_mean_mae_pct": observed["defensive_63d_mean_maximum_adverse_excursion_pct"],
        "holdout_posture_change_rate": observed["holdout_posture_change_rate"],
        "directional_return_separation_observed_not_validated": True,
        "directional_positive_rate_separation_observed_not_validated": True,
        "mae_rule_semantic_misalignment_identified": True,
        "observed_holdout_consumed_for_v1": True,
        "new_unseen_validation_required": True,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "next_decision": review["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
