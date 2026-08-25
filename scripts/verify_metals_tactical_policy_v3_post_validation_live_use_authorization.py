from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization.json"
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization_design.json"
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_unseen_validation_result_review.json"

EXPECTED_AUTH_ID = "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-1"
EXPECTED_DESIGN_ID = "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-DESIGN-1"
EXPECTED_REVIEW_ID = "METALS-TACTICAL-POLICY-V3-UNSEEN-VALIDATION-RESULT-REVIEW-1"
EXPECTED_MAPPING = {
    "TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE",
    "MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE",
    "NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY",
}
EXPECTED_CHANGE_KEYS = {
    "validated_classifier_and_mapping_are_immutable_for_v3_live_use",
    "any_classifier_formula_change_requires_new_policy_version",
    "any_threshold_logic_change_requires_new_policy_version",
    "any_action_mapping_change_requires_new_policy_version",
    "any_new_policy_version_requires_new_unseen_validation_before_live_use",
    "consumed_v1_v2_and_v3_validation_intervals_may_not_be_reused_as_unseen_evidence",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    for path in [AUTH_PATH, DESIGN_PATH, REVIEW_PATH]:
        require(path.is_file(), f"required governed file missing: {path.name}")

    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))

    require(auth["authorization_id"] == EXPECTED_AUTH_ID, "unexpected authorization id")
    require(auth["source_design_id"] == EXPECTED_DESIGN_ID, "unexpected source design id")
    require(auth["source_review_id"] == EXPECTED_REVIEW_ID, "unexpected source review id")
    require(design["design_id"] == EXPECTED_DESIGN_ID, "source design identity changed")
    require(review["review_id"] == EXPECTED_REVIEW_ID, "source review identity changed")
    require(review["review_decision"] == "VALIDATION_PASS_CONFIRMED_FOR_POST_VALIDATION_LIVE_USE_CONSIDERATION", "source review decision changed")
    require(review["controls"]["v3_unseen_validation_pass_certified"] is True, "unseen validation PASS is not certified")
    require(review["controls"]["v3_tactical_policy_validated_for_live_use_consideration"] is True, "policy is not validated for live-use consideration")

    require(auth["source_validation_result"] == "PASS", "authorization does not preserve validation PASS")
    require(auth["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1", "regime definition changed")
    require(auth["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "classifier rule changed")
    require(auth["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", "action mapping version changed")
    require(auth["authorized_mapping"] == EXPECTED_MAPPING, "authorized mapping changed")
    require(auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_V3_LIVE_TACTICAL_INTERPRETATION", "unexpected authorization decision")

    live = auth["authorized_live_use"]
    require(live["role"] == "BOUNDED_METALS_TACTICAL_INTERPRETATION_OVERLAY", "unexpected live-use role")
    require(live["current_state_materialization_authorized"] is True, "current-state materialization not authorized")
    require(live["candidate_tactical_posture_authorized"] is True, "candidate tactical posture not authorized")
    require(live["live_tactical_posture_authorized"] is True, "live tactical posture not authorized")
    require(live["point_in_time_only"] is True, "live use is not point-in-time only")
    require(live["price_basis"] == "UNADJUSTED_CLOSE", "live price basis changed")
    require(live["required_current_price_field"] == "close_usd", "live current-price field changed")
    for key in [
        "latest_certified_available_market_observation_required",
        "future_outcomes_may_not_enter_live_classification",
        "same_locked_feature_formulas_as_validated_policy",
        "same_locked_assignment_order_as_validated_policy",
        "same_locked_action_mapping_as_validated_policy",
        "reference_control_bil_remains_non_opportunity",
    ]:
        require(live[key] is True, f"live-use boundary missing: {key}")

    limits = auth["interpretation_limits"]
    for key, value in limits.items():
        require(value is True, f"interpretation limit missing: {key}")

    output = auth["live_output_contract"]
    required_fields = set(output["required_fields"])
    for field in [
        "asset_id", "ticker", "as_of_date", "candidate_regime", "tactical_state",
        "classifier_rule_version", "action_mapping_version", "price_semantics",
        "source_package_id", "state_available", "state_reason",
    ]:
        require(field in required_fields, f"required live output field missing: {field}")
    require(output["state_labels"] == {
        "TACTICAL_SUPPORTIVE": "Supportive",
        "TACTICAL_DEFENSIVE": "Defensive",
        "NO_TACTICAL_OVERLAY": "Neutral / No Overlay",
    }, "presentation state labels changed")
    require(output["raw_validation_outcomes_may_not_be_presented_as_current_forecasts"] is True, "validation outcomes could be misused as forecasts")
    require(output["historical_validation_statistics_may_be_used_only_as_provenance_or_methodology_context"] is True, "validation methodology context boundary changed")

    freshness = auth["freshness_and_fail_closed_controls"]
    for key, value in freshness.items():
        require(value is True, f"freshness/fail-closed control missing: {key}")

    change = auth["change_control"]
    require(set(change.keys()) == EXPECTED_CHANGE_KEYS, "change-control exact key set changed")
    for key in EXPECTED_CHANGE_KEYS:
        require(change[key] is True, f"change-control boundary missing: {key}")

    downstream = auth["downstream_authorization_boundary"]
    for key, value in downstream.items():
        require(value is False, f"downstream authority prematurely enabled: {key}")

    require(auth["next_decision"] == "IMPLEMENT_METALS_TACTICAL_POLICY_V3_CURRENT_STATE_MATERIALIZATION", "unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "authorization_decision": auth["authorization_decision"],
        "source_validation_result": auth["source_validation_result"],
        "live_use_role": live["role"],
        "current_state_materialization_authorized": live["current_state_materialization_authorized"],
        "live_tactical_posture_authorized": live["live_tactical_posture_authorized"],
        "price_basis": live["price_basis"],
        "point_in_time_only": live["point_in_time_only"],
        "production_database_write_authorized": downstream["production_database_write_authorized"],
        "presentation_activation_authorized": downstream["presentation_activation_authorized"],
        "allocation_policy_authorized": downstream["allocation_policy_authorized"],
        "automatic_execution_authorized": downstream["automatic_execution_authorized"],
        "next_decision": auth["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
