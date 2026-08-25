from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization_design.json"
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_unseen_validation_result_review.json"

EXPECTED_DESIGN_ID = "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-DESIGN-1"
EXPECTED_REVIEW_ID = "METALS-TACTICAL-POLICY-V3-UNSEEN-VALIDATION-RESULT-REVIEW-1"
EXPECTED_MAPPING = {
    "TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE",
    "MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE",
    "NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY",
}
EXPECTED_CHAIN = [
    "LONG_TERM_THESIS",
    "MEDIUM_TERM_OPPORTUNITY",
    "MOMENTUM_AND_REGIME",
    "TACTICAL_POSITION",
    "RISK_AND_DOWNSIDE",
    "WHY",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(DESIGN_PATH.is_file(), "live-use authorization design is missing")
    require(REVIEW_PATH.is_file(), "certified unseen-validation review is missing")

    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))

    require(design["design_id"] == EXPECTED_DESIGN_ID, "unexpected design id")
    require(design["source_review_id"] == EXPECTED_REVIEW_ID, "unexpected source review id")
    require(review["review_id"] == EXPECTED_REVIEW_ID, "review identity changed")
    require(review["review_decision"] == "VALIDATION_PASS_CONFIRMED_FOR_POST_VALIDATION_LIVE_USE_CONSIDERATION", "source review is not approved for live-use consideration")
    require(review["controls"]["v3_unseen_validation_pass_certified"] is True, "unseen validation PASS is not certified")
    require(review["controls"]["v3_tactical_policy_validated_for_live_use_consideration"] is True, "policy is not validated for live-use consideration")
    require(review["controls"]["live_tactical_posture_authorized"] is False, "live tactical posture was prematurely authorized")

    require(design["source_validation_result"] == "PASS", "design does not preserve validation PASS")
    require(design["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1", "regime definition changed")
    require(design["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "classifier rule changed")
    require(design["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", "action mapping version changed")
    require(design["validated_mapping"] == EXPECTED_MAPPING, "validated mapping changed")

    role = design["live_use_role_design"]
    require(role["role"] == "BOUNDED_METALS_TACTICAL_INTERPRETATION_OVERLAY", "unexpected live-use role")
    for key in [
        "not_a_buy_signal",
        "not_a_sell_signal",
        "not_position_sizing",
        "not_portfolio_allocation",
        "not_expected_return_forecast",
        "not_long_term_thesis",
        "not_medium_term_opportunity_score",
        "not_risk_override",
    ]:
        require(role[key] is True, f"live-use role boundary missing: {key}")

    require(design["planned_uip_interpretation_chain"] == EXPECTED_CHAIN, "UIP interpretation chain changed")

    precedence = design["precedence_and_non_override_rules"]
    for key in [
        "long_term_thesis_remains_independent",
        "medium_term_opportunity_remains_independent",
        "risk_and_downside_remain_independent",
        "tactical_overlay_may_not_convert_a_non_opportunity_into_an_opportunity_by_itself",
        "tactical_overlay_may_not_suppress_or_hide_material_risk",
        "tactical_overlay_may_not_override_domain_governance",
        "neutral_state_may_not_be_forced_directional",
        "duplicate_exposure_families_may_not_be_treated_as_independent_confirmation",
    ]:
        require(precedence[key] is True, f"precedence boundary missing: {key}")

    live = design["live_calculation_design"]
    require(live["price_basis"] == "UNADJUSTED_CLOSE", "live price basis changed")
    require(live["required_current_price_field"] == "close_usd", "live current-price field changed")
    require(live["classifier_rule_version_must_remain"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "live classifier version changed")
    require(live["action_mapping_version_must_remain"] == "METALS-V3-ACTION-MAPPING-1", "live action mapping changed")
    for key in [
        "point_in_time_only",
        "future_outcomes_may_not_enter_live_classification",
        "adaptive_thresholds_use_prior_observations_only",
        "same_locked_feature_formulas_as_validated_policy",
        "same_locked_assignment_order_as_validated_policy",
        "same_locked_action_mapping_as_validated_policy",
        "reference_control_bil_remains_non_opportunity",
    ]:
        require(live[key] is True, f"live calculation boundary missing: {key}")

    freshness = design["freshness_and_fail_closed_design"]
    for key in [
        "current_state_must_be_based_on_latest_certified_available_market_observation",
        "state_as_of_date_must_be_persisted",
        "source_package_id_or_equivalent_provenance_must_be_persisted",
        "classifier_version_must_be_persisted",
        "action_mapping_version_must_be_persisted",
        "stale_or_missing_required_history_must_not_produce_directional_live_state",
        "incomplete_feature_history_must_fail_to_no_tactical_overlay_or_unavailable",
        "unmapped_regime_must_fail_closed",
        "price_semantics_mismatch_must_fail_closed",
        "classifier_or_mapping_version_mismatch_must_fail_closed",
    ]:
        require(freshness[key] is True, f"freshness/fail-closed boundary missing: {key}")

    output = design["planned_live_output_contract"]
    required_fields = set(output["required_fields"])
    for field in [
        "asset_id", "ticker", "as_of_date", "candidate_regime", "tactical_state",
        "classifier_rule_version", "action_mapping_version", "price_semantics",
        "source_package_id", "state_available", "state_reason",
    ]:
        require(field in required_fields, f"required live output field missing: {field}")
    require(output["raw_validation_outcomes_may_not_be_presented_as_current_forecasts"] is True, "validation outcomes could be misused as forecasts")
    require(output["historical_validation_statistics_may_be_used_only_as provenance_or_methodology_context"] is True, "historical validation context boundary changed")

    presentation = design["planned_presentation_semantics"]
    require(presentation["TACTICAL_SUPPORTIVE"] == "Supportive", "supportive presentation changed")
    require(presentation["TACTICAL_DEFENSIVE"] == "Defensive", "defensive presentation changed")
    require(presentation["NO_TACTICAL_OVERLAY"] == "Neutral / No Overlay", "neutral presentation changed")
    require(presentation["must_include_as_of_date"] is True, "presentation as-of date boundary missing")
    require(presentation["must_include_methodology_or_rationale_linkage"] is True, "presentation rationale boundary missing")
    require(presentation["must_not_display_as_buy_hold_sell"] is True, "presentation could become buy/hold/sell")
    require(presentation["must_not_display_as_probability_of_gain"] is True, "presentation could become gain probability")
    require(presentation["must_not_display_as_position_size"] is True, "presentation could become position sizing")

    change = design["change_control_design"]
    for key in [
        "validated_classifier_and_mapping_are_immutable_for_v3_live_use",
        "any_classifier_formula_change_requires_new_policy_version",
        "any threshold_logic_change_requires_new_policy_version",
        "any_action_mapping_change_requires_new_policy_version",
        "any_new_policy_version_requires_new_unseen_validation_before_live_use",
        "consumed_v1_v2_and_v3_validation_intervals_may_not_be_reused_as_unseen_evidence",
    ]:
        require(change[key] is True, f"change-control boundary missing: {key}")

    boundary = design["authorization_boundary"]
    require(boundary["design_complete"] is True, "live-use design is not complete")
    for key in [
        "live_use_authorization_created",
        "candidate_tactical_posture_authorized",
        "live_tactical_posture_authorized",
        "production_database_write_authorized",
        "presentation_activation_authorized",
        "native_source_query_authorized",
        "network_collection_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ]:
        require(boundary[key] is False, f"downstream authority prematurely enabled: {key}")

    require(design["next_decision"] == "CONSIDER_METALS_TACTICAL_POLICY_V3_POST_VALIDATION_LIVE_USE_AUTHORIZATION", "unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "design_id": design["design_id"],
        "source_review_id": design["source_review_id"],
        "source_validation_result": design["source_validation_result"],
        "live_use_role": role["role"],
        "validated_mapping": design["validated_mapping"],
        "price_basis": live["price_basis"],
        "point_in_time_only": live["point_in_time_only"],
        "design_complete": boundary["design_complete"],
        "live_use_authorization_created": boundary["live_use_authorization_created"],
        "live_tactical_posture_authorized": boundary["live_tactical_posture_authorized"],
        "production_database_write_authorized": boundary["production_database_write_authorized"],
        "presentation_activation_authorized": boundary["presentation_activation_authorized"],
        "next_decision": design["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
