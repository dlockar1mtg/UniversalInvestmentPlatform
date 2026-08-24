from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "metals" / "tactical_policy_v2_research_design.json"


def main() -> int:
    cfg = json.loads(CONTRACT.read_text(encoding="utf-8"))

    if cfg.get("design_id") != "METALS-TACTICAL-POLICY-V2-RESEARCH-DESIGN-1":
        raise RuntimeError("unexpected V2 research design")
    if cfg.get("source_v1_review") != "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-REVIEW-1":
        raise RuntimeError("unexpected V1 review source")

    v1 = cfg.get("v1_findings") or {}
    if v1.get("candidate_v1_result") != "INCONCLUSIVE":
        raise RuntimeError("V1 result changed")
    if int(v1.get("constructive_holdout_observations", -1)) != 280:
        raise RuntimeError("constructive V1 support changed")
    if int(v1.get("defensive_holdout_observations", -1)) != 15:
        raise RuntimeError("defensive V1 support changed")
    if int(v1.get("minimum_supported_observations_per_compared_group", -1)) != 20:
        raise RuntimeError("minimum support changed")
    if v1.get("minimum_group_support_met") is not False:
        raise RuntimeError("V1 support result changed")
    for key in (
        "directional_return_separation_observed_not_validated",
        "directional_positive_rate_separation_observed_not_validated",
        "mae_rule_semantic_misalignment_identified",
        "observed_v1_evaluation_evidence_consumed",
    ):
        if v1.get(key) is not True:
            raise RuntimeError(f"V1 finding not preserved: {key}")

    req = cfg.get("v2_research_requirements") or {}
    required_true = (
        "new_candidate_version_required",
        "v1_candidate_may_not_be_relabelled_as_pass",
        "v1_observed_outcomes_may_inform_research_but_not_validate_v2",
        "bil_remains_reference_control_only",
        "time_aligned_price_derived_historical_inputs_only",
        "current_only_recommendation_or_risk_backfill_prohibited",
        "candidate_rule_changes_must_be_explicitly_versioned",
        "candidate_rules_must_be_locked_before_new_validation_outcomes_are_inspected",
        "defensive_group_support_must_be_addressed_before_final_validation",
        "defensive_signal_is_a_warning_of_worse_subsequent_outcomes_not_a_low_drawdown_state",
        "corrected_downside_validation_direction_required",
        "new_unseen_validation_evidence_required",
    )
    for key in required_true:
        if req.get(key) is not True:
            raise RuntimeError(f"required V2 research constraint changed: {key}")

    expected_postures = {"ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"}
    if set(req.get("five_posture_vocabulary_preserved_for_research") or []) != expected_postures:
        raise RuntimeError("V2 posture vocabulary changed")

    unseen = cfg.get("unseen_validation_strategy") or {}
    if unseen.get("strategy") != "GOVERNED_HISTORICAL_EXPANSION_ACQUIRED_AFTER_V2_RULE_LOCK":
        raise RuntimeError("unexpected unseen validation strategy")
    if unseen.get("existing_certified_history_start_date") != "2023-08-22":
        raise RuntimeError("existing history start changed")
    if unseen.get("existing_certified_history_end_date") != "2026-08-21":
        raise RuntimeError("existing history end changed")
    for key in (
        "v1_outcomes_from_existing_history_are_consumed",
        "expanded_history_must_end_before_existing_certified_history_start_date",
        "expanded_history_outcomes_may_not_be_inspected_before_v2_rule_lock",
        "network_or_native_history_collection_not_authorized_by_this_design",
        "historical_expansion_feasibility_must_be_audited_after_v2_rule_lock",
        "minimum_common_history_start_date_must_be_discovered_not_assumed",
        "new_validation_interval_must_be_disjoint_from_v1_evaluation_interval",
    ):
        if unseen.get(key) is not True:
            raise RuntimeError(f"unseen-validation safeguard changed: {key}")

    scope = cfg.get("v2_candidate_design_scope") or {}
    for key in (
        "may_revise_signal_thresholds",
        "may_revise_signal_weights",
        "may_revise_posture_score_boundaries",
        "may_revise_downside_pass_fail_semantics",
        "may_not_use_new_unseen_outcomes_during_rule_design",
        "may_not_reduce_minimum_compared_group_support_below_20",
        "must_preserve_no_missing_authority_synthesis",
        "must_preserve_forecast_validation_separate_from_policy_validation",
    ):
        if scope.get(key) is not True:
            raise RuntimeError(f"V2 candidate-design scope changed: {key}")

    controls = cfg.get("controls") or {}
    if controls.get("v2_research_design_authorized") is not True:
        raise RuntimeError("V2 research design not authorized")
    for key in (
        "v2_candidate_rule_design_authorized",
        "historical_expansion_execution_authorized",
        "new_validation_outcome_inspection_authorized",
        "historical_candidate_evaluation_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited control changed unexpectedly: {key}")

    if cfg.get("next_decision") != "AUTHORIZE_METALS_TACTICAL_POLICY_V2_CANDIDATE_RULE_DESIGN":
        raise RuntimeError("unexpected next decision")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": cfg["design_id"],
        "source_v1_review": cfg["source_v1_review"],
        "candidate_v1_result": v1["candidate_v1_result"],
        "constructive_holdout_observations": int(v1["constructive_holdout_observations"]),
        "defensive_holdout_observations": int(v1["defensive_holdout_observations"]),
        "minimum_supported_observations_per_compared_group": int(v1["minimum_supported_observations_per_compared_group"]),
        "v1_holdout_consumed": True,
        "mae_rule_semantic_misalignment_preserved": True,
        "new_unseen_validation_required": True,
        "v2_rules_must_lock_before_new_outcomes": True,
        "historical_expansion_execution_authorized": False,
        "new_validation_outcome_inspection_authorized": False,
        "v2_candidate_rule_design_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "next_decision": cfg["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
