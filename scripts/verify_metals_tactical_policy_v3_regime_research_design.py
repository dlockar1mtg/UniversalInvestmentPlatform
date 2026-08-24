from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_research_design.json"
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_regime_research_design.json"


def main() -> int:
    parent = json.loads(PARENT_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    if parent.get("design_id") != "METALS-TACTICAL-POLICY-V3-RESEARCH-DESIGN-1":
        raise RuntimeError("unexpected parent v3 research design")
    if parent.get("next_decision") != "AUTHORIZE_METALS_TACTICAL_POLICY_V3_REGIME_RESEARCH_DESIGN":
        raise RuntimeError("parent v3 research-design next decision changed")

    if design.get("design_id") != "METALS-TACTICAL-POLICY-V3-REGIME-RESEARCH-DESIGN-1":
        raise RuntimeError("unexpected v3 regime research design")
    if design.get("source_v3_research_design") != parent.get("design_id"):
        raise RuntimeError("unexpected parent v3 research-design source")
    if design.get("source_v2_failed_validation_review") != "METALS-TACTICAL-POLICY-V2-FAILED-VALIDATION-REVIEW-1":
        raise RuntimeError("unexpected v2 failed-validation review source")

    boundary = design.get("research_boundary") or {}
    for key in (
        "consumed_v1_v2_evidence_may_be_used_for_research_and_development_only",
        "consumed_v1_v2_intervals_may_not_be_called_unseen_again",
        "regime_classification_must_remain_separate_from_action_mapping",
        "regime_research_must_not_assign_live_or_candidate_tactical_postures",
        "new_validation_outcomes_may_not_be_inspected",
        "production_database_writes_prohibited",
        "presentation_activation_prohibited",
        "model_retraining_prohibited",
        "cross_domain_rank_prohibited",
        "allocation_policy_prohibited",
        "automatic_execution_prohibited",
    ):
        if boundary.get(key) is not True:
            raise RuntimeError(f"regime research boundary missing: {key}")

    regimes = design.get("candidate_regime_families") or []
    expected_regimes = ["TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION", "NEUTRAL_OR_UNCERTAIN"]
    actual_regimes = [item.get("regime_id") for item in regimes]
    if actual_regimes != expected_regimes:
        raise RuntimeError("candidate regime families changed")
    if regimes[0].get("must_distinguish_trend_strength_from_persistence") is not True:
        raise RuntimeError("trend strength/persistence distinction missing")
    if regimes[1].get("must_not_infer_predictive_mean_reversion_from_v2_failure_alone") is not True:
        raise RuntimeError("v2 mean-reversion semantic guard missing")
    if regimes[2].get("conflicting_evidence_must_be_allowed_to_resolve_to_neutral") is not True:
        raise RuntimeError("neutral conflict-resolution requirement missing")
    if regimes[2].get("insufficient_support_must_be_allowed_to_resolve_to_neutral") is not True:
        raise RuntimeError("neutral insufficient-support requirement missing")

    inputs = design.get("candidate_input_registry") or {}
    for key in (
        "inputs_must_be_point_in_time",
        "future_returns_or_future_excursions_prohibited_as_classifier_inputs",
        "current_only_recommendation_or_risk_fields_prohibited_from_historical_backfill",
        "missing_historical_vintage_authority_must_remain_missing",
        "additional_candidate_inputs_are_research_candidates_not_final_authorized_features",
    ):
        if inputs.get(key) is not True:
            raise RuntimeError(f"candidate input control missing: {key}")
    expected_existing = [
        "return_1m_pct",
        "return_3m_pct",
        "return_6m_pct",
        "distance_ma50_pct",
        "distance_ma200_pct",
        "current_drawdown_pct",
        "realized_volatility_3m_pct",
    ]
    if inputs.get("existing_inputs") != expected_existing:
        raise RuntimeError("existing research inputs changed")
    expected_candidates = [
        "trend_slope",
        "return_dispersion",
        "volatility_change",
        "drawdown_recovery_rate",
        "distance_from_recent_extreme",
        "short_vs_long_momentum_spread",
    ]
    if inputs.get("additional_candidate_inputs_to_define_before_execution") != expected_candidates:
        raise RuntimeError("additional candidate input registry changed")

    questions = design.get("research_questions") or []
    if len(questions) < 6:
        raise RuntimeError("insufficient regime research questions")

    method = design.get("research_method") or {}
    if method.get("historical_study_role") != "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE":
        raise RuntimeError("historical study role changed")
    for key in (
        "classifier_inputs_must_be_frozen_before_historical_regime_study_execution",
        "candidate_regime_assignment_logic_must_be_versioned",
        "research_may_compare_subsequent_outcomes_only_after_point_in_time_regime_labels_are_generated",
        "subsequent_outcomes_are_research_targets_not_classifier_inputs",
        "overlapping_forward_windows_must_be_disclosed",
        "minimum_compared_group_support_may_not_be_lowered_below_20",
        "regime_separability_must_be_reviewed_before_regime_definition_lock",
        "regime_support_must_be_reviewed_before_regime_definition_lock",
        "no_regime_family_may_be_forced_when_evidence_is_conflicting",
    ):
        if method.get(key) is not True:
            raise RuntimeError(f"regime research method requirement missing: {key}")
    if int(method.get("minimum_compared_group_support", -1)) != 20:
        raise RuntimeError("minimum compared-group support changed")

    exposure = design.get("exposure_family_controls") or {}
    for key in (
        "bil_is_reference_control_only",
        "bil_may_not_be_treated_as_an_opportunity",
        "duplicate_exposure_families_are_not_independent_confirmation",
        "family_coverage_requirements_must_be_defined_before_validation",
        "regime_support_requirements_must_be_defined_before_validation",
        "validation_may_not_count_duplicate_family_members_as_independent_confirmations",
    ):
        if exposure.get(key) is not True:
            raise RuntimeError(f"exposure-family control missing: {key}")
    if exposure.get("known_non_independent_groups") != [["GLD", "IAU", "SGOL"], ["SIVR", "SLV"]]:
        raise RuntimeError("known non-independent exposure groups changed")

    required_outputs = design.get("required_research_outputs_before_regime_definition_lock") or []
    if len(required_outputs) < 8:
        raise RuntimeError("required research-output registry incomplete")

    controls = design.get("controls") or {}
    if controls.get("v3_research_design_authorized") is not True:
        raise RuntimeError("parent v3 research design is not authorized")
    if controls.get("v3_regime_research_design_authorized") is not True:
        raise RuntimeError("v3 regime research design is not authorized")
    for key in (
        "v3_regime_definition_authorized",
        "v3_candidate_rule_design_authorized",
        "v3_historical_regime_research_execution_authorized",
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
            raise RuntimeError(f"prohibited regime-research control changed unexpectedly: {key}")

    if design.get("next_decision") != "AUTHORIZE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH":
        raise RuntimeError("unexpected regime research next decision")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": design["design_id"],
        "source_v3_research_design": design["source_v3_research_design"],
        "candidate_regime_family_count": len(regimes),
        "research_question_count": len(questions),
        "minimum_support_floor": method["minimum_compared_group_support"],
        "trend_strength_persistence_distinction_required": regimes[0]["must_distinguish_trend_strength_from_persistence"],
        "neutral_conflict_resolution_required": regimes[2]["conflicting_evidence_must_be_allowed_to_resolve_to_neutral"],
        "bil_reference_control_only": exposure["bil_is_reference_control_only"],
        "known_non_independent_group_count": len(exposure["known_non_independent_groups"]),
        "v3_regime_research_design_authorized": controls["v3_regime_research_design_authorized"],
        "v3_regime_definition_authorized": controls["v3_regime_definition_authorized"],
        "v3_historical_regime_research_execution_authorized": controls["v3_historical_regime_research_execution_authorized"],
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
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
