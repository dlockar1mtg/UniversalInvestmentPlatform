from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_research_design.json"


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    if design.get("design_id") != "METALS-TACTICAL-POLICY-V3-RESEARCH-DESIGN-1":
        raise RuntimeError("unexpected v3 research design")
    if design.get("source_v2_failed_validation_review") != "METALS-TACTICAL-POLICY-V2-FAILED-VALIDATION-REVIEW-1":
        raise RuntimeError("unexpected v2 failed-validation review source")
    if design.get("source_v2_evaluation") != "METALS-TACTICAL-POLICY-V2-VALIDATION-EVALUATION-1":
        raise RuntimeError("unexpected v2 evaluation source")

    evidence = design.get("preserved_evidence") or {}
    if evidence.get("v1_result") != "INCONCLUSIVE":
        raise RuntimeError("v1 result changed")
    if evidence.get("v2_result") != "FAIL":
        raise RuntimeError("v2 result changed")
    if evidence.get("v2_failure_support_limited") is not False:
        raise RuntimeError("v2 failure incorrectly treated as support-limited")
    if int(evidence.get("v2_directional_check_failures", -1)) != 3:
        raise RuntimeError("v2 directional failure count changed")
    if int(evidence.get("v2_constructive_63d_observations", -1)) != 489:
        raise RuntimeError("v2 constructive support changed")
    if int(evidence.get("v2_defensive_63d_observations", -1)) != 639:
        raise RuntimeError("v2 defensive support changed")
    if evidence.get("v2_validation_interval_consumed") is not True:
        raise RuntimeError("v2 validation interval no longer marked consumed")
    if evidence.get("v2_live_use_authorized") is not False:
        raise RuntimeError("v2 live use unexpectedly authorized")

    findings = design.get("research_findings") or {}
    if findings.get("single_monotonic_trend_score_not_supported_for_live_use") is not True:
        raise RuntimeError("v2 failed-direction finding missing")
    if findings.get("observed_inversion_is_research_evidence_not_live_mean_reversion_authority") is not True:
        raise RuntimeError("mean-reversion evidence semantic guard missing")
    if findings.get("regime_dependence_is_a_hypothesis_requiring_new_design_and validation") is not True:
        raise RuntimeError("regime-dependence hypothesis guard missing")

    architecture = design.get("v3_architecture_direction") or {}
    expected_regimes = ["TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION", "NEUTRAL_OR_UNCERTAIN"]
    if architecture.get("candidate_regime_families") != expected_regimes:
        raise RuntimeError("candidate regime families changed")
    for key in (
        "regime_aware_framework_required",
        "single_unconditional_constructive_defensive_mapping_prohibited",
        "regime_classifier_must_be_separate_from_action_mapping",
        "regime_classifier_must_use_point_in_time_inputs_only",
        "regime_classifier_may_not_use_future_returns_or_future_excursions",
        "action_mapping_must_be_conditioned_on_certified_regime_authority",
        "neutral_or_uncertain_regime_must_allow_no_action",
        "candidate_postures_may_not_be_assigned_until_separately_authorized",
    ):
        if architecture.get(key) is not True:
            raise RuntimeError(f"v3 architecture requirement missing: {key}")

    methods = design.get("research_method_requirements") or {}
    for key in (
        "v1_and_v2_consumed_outcomes_may_be_used_for_research_hypothesis_generation",
        "v1_or_v2_consumed_intervals_may_not_be_called_unseen_again",
        "v3_candidate_rules_must_be_versioned",
        "v3_regime_definition_must_be_locked_before_any_new_unseen_validation_outcomes_are_inspected",
        "v3_action_mapping_must_be_locked_before_any_new_unseen_validation_outcomes_are_inspected",
        "new_unseen_validation_authority_required_before_live_use",
        "duplicate_exposure_families_must_not_be_treated_as_independent_confirmation",
        "overlapping_forward_windows_must_be_disclosed",
        "family_coverage_and_regime_support_requirements_must_be_defined_before_validation",
    ):
        if methods.get(key) is not True:
            raise RuntimeError(f"v3 research method requirement missing: {key}")
    if int(methods.get("minimum_compared_group_support_may_not_be_lowered_below_20", -1)) != 20:
        raise RuntimeError("minimum support floor changed")

    controls = design.get("controls") or {}
    if controls.get("v3_research_design_authorized") is not True:
        raise RuntimeError("v3 research design is not authorized")
    for key in (
        "v3_regime_definition_authorized",
        "v3_candidate_rule_design_authorized",
        "v3_historical_research_execution_authorized",
        "new_validation_data_collection_authorized",
        "new_validation_outcome_inspection_authorized",
        "historical_candidate_evaluation_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "native_source_query_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited v3 control changed unexpectedly: {key}")

    if design.get("next_decision") != "AUTHORIZE_METALS_TACTICAL_POLICY_V3_REGIME_RESEARCH_DESIGN":
        raise RuntimeError("unexpected v3 next decision")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": design["design_id"],
        "source_v2_failed_validation_review": design["source_v2_failed_validation_review"],
        "v1_result": evidence["v1_result"],
        "v2_result": evidence["v2_result"],
        "v2_directional_check_failures": evidence["v2_directional_check_failures"],
        "v2_constructive_63d_observations": evidence["v2_constructive_63d_observations"],
        "v2_defensive_63d_observations": evidence["v2_defensive_63d_observations"],
        "v2_validation_interval_consumed": evidence["v2_validation_interval_consumed"],
        "regime_aware_framework_required": architecture["regime_aware_framework_required"],
        "candidate_regime_family_count": len(architecture["candidate_regime_families"]),
        "minimum_support_floor": methods["minimum_compared_group_support_may_not_be_lowered_below_20"],
        "v3_regime_definition_authorized": controls["v3_regime_definition_authorized"],
        "v3_candidate_rule_design_authorized": controls["v3_candidate_rule_design_authorized"],
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": controls["cross_domain_rank_authorized"],
        "allocation_policy_authorized": controls["allocation_policy_authorized"],
        "automatic_execution_authorized": controls["automatic_execution_authorized"],
        "next_decision": design["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
