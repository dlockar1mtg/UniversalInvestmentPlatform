from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_regime_research_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_authorization.json"


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    if design.get("design_id") != "METALS-TACTICAL-POLICY-V3-REGIME-RESEARCH-DESIGN-1":
        raise RuntimeError("unexpected v3 regime research design")
    if design.get("next_decision") != "AUTHORIZE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH":
        raise RuntimeError("parent design does not authorize this decision point")
    if auth.get("authorization_id") != "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-AUTHORIZATION-1":
        raise RuntimeError("unexpected historical regime research authorization")
    if auth.get("source_v3_regime_research_design") != design.get("design_id"):
        raise RuntimeError("authorization source design mismatch")
    if auth.get("decision") != "AUTHORIZE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH":
        raise RuntimeError("unexpected authorization decision")

    scope = auth.get("authorization_scope") or {}
    if scope.get("historical_regime_research_execution_authorized") is not True:
        raise RuntimeError("historical regime research execution not authorized")
    if scope.get("research_role") != "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE":
        raise RuntimeError("historical regime research role changed")
    for key in (
        "consumed_v1_v2_evidence_may_be_used_for_hypothesis_development",
        "consumed_v1_v2_intervals_may_not_be_called_unseen_again",
        "point_in_time_regime_labels_must_be_generated_before_subsequent_outcomes_are_compared",
        "subsequent_outcomes_may_be_used_only_as_research_targets",
        "research_results_must_be_labelled_development_evidence_not_unseen_validation",
    ):
        if scope.get(key) is not True:
            raise RuntimeError(f"authorization scope requirement missing: {key}")

    freeze = auth.get("pre_execution_freeze_requirements") or {}
    for key in (
        "candidate_input_definitions_must_be_versioned_and_frozen_before_execution",
        "candidate_regime_assignment_logic_must_be_versioned_and_frozen_before_execution",
        "future_returns_or_future_excursions_may_not_be_classifier_inputs",
        "current_only_recommendation_or_risk_fields_may_not_be_backfilled_historically",
        "missing_historical_vintage_authority_must_remain_missing",
        "minimum_compared_group_support_may_not_be_lowered",
    ):
        if freeze.get(key) is not True:
            raise RuntimeError(f"pre-execution freeze requirement missing: {key}")
    if int(freeze.get("minimum_compared_group_support", -1)) != 20:
        raise RuntimeError("minimum support floor changed")

    expected_regimes = ["TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION", "NEUTRAL_OR_UNCERTAIN"]
    if auth.get("authorized_candidate_regime_families") != expected_regimes:
        raise RuntimeError("authorized candidate regime families changed")

    input_scope = auth.get("authorized_candidate_input_research_scope") or {}
    if input_scope.get("trend_strength_must_be_distinguished_from_trend_persistence") is not True:
        raise RuntimeError("trend strength/persistence guard missing")
    if input_scope.get("conflicting_or_weak_evidence_must_be_allowed_to_resolve_to_neutral_or_uncertain") is not True:
        raise RuntimeError("neutral/conflict guard missing")
    if input_scope.get("additional_candidate_inputs_are_not_final_authorized_production_features") is not True:
        raise RuntimeError("candidate input semantic guard missing")

    exposure = auth.get("exposure_family_controls") or {}
    if exposure.get("bil_is_reference_control_only") is not True:
        raise RuntimeError("BIL reference/control restriction changed")
    if exposure.get("bil_may_not_be_treated_as_an_opportunity") is not True:
        raise RuntimeError("BIL opportunity restriction changed")
    if exposure.get("duplicate_exposure_families_are_not_independent_confirmation") is not True:
        raise RuntimeError("duplicate family independence restriction changed")
    if exposure.get("known_non_independent_groups") != [["GLD", "IAU", "SGOL"], ["SIVR", "SLV"]]:
        raise RuntimeError("known non-independent exposure groups changed")
    if exposure.get("support_must_be_reported_by_exposure_family") is not True:
        raise RuntimeError("exposure-family support reporting requirement missing")

    required_outputs = auth.get("required_execution_outputs") or []
    if len(required_outputs) != 10:
        raise RuntimeError("unexpected required execution output count")

    review = auth.get("post_execution_review_requirements") or {}
    for key in (
        "regime_support_must_be_reviewed_before_regime_definition_lock",
        "regime_separability_must_be_reviewed_before_regime_definition_lock",
        "conflict_and_neutral_behavior_must_be_reviewed_before_regime_definition_lock",
        "no_regime_definition_may_be_locked_automatically_from_execution_results",
        "separate_governance_decision_required_to_lock_v3_regime_definition",
    ):
        if review.get(key) is not True:
            raise RuntimeError(f"post-execution review requirement missing: {key}")

    prohibited = auth.get("prohibited_authorities") or {}
    for key in (
        "new_validation_data_collection_authorized",
        "new_validation_outcome_inspection_authorized",
        "unseen_validation_claim_authorized",
        "v3_regime_definition_authorized",
        "v3_candidate_rule_design_authorized",
        "action_mapping_authorized",
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
        if prohibited.get(key) is not False:
            raise RuntimeError(f"prohibited authority changed unexpectedly: {key}")

    controls = auth.get("controls") or {}
    for key in (
        "v3_research_design_authorized",
        "v3_regime_research_design_authorized",
        "v3_historical_regime_research_authorized",
        "v3_historical_regime_research_execution_authorized",
    ):
        if controls.get(key) is not True:
            raise RuntimeError(f"required authorization control missing: {key}")
    for key in (
        "v3_regime_definition_authorized",
        "v3_candidate_rule_design_authorized",
        "new_validation_outcome_inspection_authorized",
        "tactical_posture_authorized",
        "production_database_write_authorized",
        "presentation_activation_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"downstream control unexpectedly authorized: {key}")

    if auth.get("next_decision") != "EXECUTE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH":
        raise RuntimeError("unexpected next decision")

    result = {
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "source_v3_regime_research_design": auth["source_v3_regime_research_design"],
        "historical_regime_research_execution_authorized": scope["historical_regime_research_execution_authorized"],
        "research_role": scope["research_role"],
        "candidate_regime_family_count": len(auth["authorized_candidate_regime_families"]),
        "minimum_support_floor": freeze["minimum_compared_group_support"],
        "required_execution_output_count": len(required_outputs),
        "known_non_independent_group_count": len(exposure["known_non_independent_groups"]),
        "bil_reference_control_only": exposure["bil_is_reference_control_only"],
        "development_not_validation_required": scope["research_results_must_be_labelled_development_evidence_not_unseen_validation"],
        "regime_definition_authorized": controls["v3_regime_definition_authorized"],
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": controls["cross_domain_rank_authorized"],
        "allocation_policy_authorized": controls["allocation_policy_authorized"],
        "automatic_execution_authorized": controls["automatic_execution_authorized"],
        "next_decision": auth["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
