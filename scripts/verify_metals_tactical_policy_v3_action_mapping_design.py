from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_action_mapping_design.json"
LOCK_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_regime_definition_lock_decision.json"


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    if design.get("design_id") != "METALS-TACTICAL-POLICY-V3-ACTION-MAPPING-DESIGN-1":
        raise RuntimeError("unexpected action mapping design")
    if lock.get("decision_id") != "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-LOCK-DECISION-1":
        raise RuntimeError("unexpected source regime lock decision")
    if design.get("source_regime_definition") != lock["locked_regime_definition"]["definition_id"]:
        raise RuntimeError("action mapping design is not bound to locked regime definition")
    if design.get("source_classifier_rule_version") != lock["locked_regime_definition"]["classifier_rule_version"]:
        raise RuntimeError("classifier rule version changed")
    if design.get("source_label_ledger_sha256") != lock["source_label_ledger_sha256"]:
        raise RuntimeError("label ledger authority changed")

    principles = design["design_principles"]
    required_true = (
        "regime_classifier_is_locked_and_may_not_be_changed_by_this_design",
        "mapping_is_ordinal_not_position_sizing",
        "mapping_does_not_authorize_buy_sell_or_trade_execution",
        "mapping_uses_only_locked_regime_labels",
        "no_current_only_recommendation_or_risk_field_is_an_input",
        "no_future_return_or_excursion_is_an_input",
        "neutral_or_uncertain_must_remain_fail_closed",
        "bil_remains_reference_control_only",
        "duplicate_exposure_families_are_not_independent_confirmation",
    )
    for key in required_true:
        if principles.get(key) is not True:
            raise RuntimeError(f"required action mapping design principle changed: {key}")

    mapping = design["candidate_action_mapping"]
    if mapping.get("mapping_version") != "METALS-V3-ACTION-MAPPING-1":
        raise RuntimeError("unexpected action mapping version")
    expected = {
        "TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE",
        "MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE",
        "NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY",
    }
    for regime, action in expected.items():
        entry = mapping.get(regime) or {}
        if entry.get("candidate_action_state") != action:
            raise RuntimeError(f"unexpected candidate action mapping for {regime}")
        if entry.get("position_size_change_authorized") is not False:
            raise RuntimeError(f"position sizing unexpectedly authorized for {regime}")
        if entry.get("trade_execution_authorized") is not False:
            raise RuntimeError(f"trade execution unexpectedly authorized for {regime}")

    hypothesis = design["unseen_validation_hypothesis"]
    for key in (
        "supportive_median_return_should_exceed_defensive",
        "supportive_positive_return_rate_should_exceed_defensive",
        "supportive_mean_mae_should_be_less_negative_than_defensive",
        "all_three_directional_checks_required_at_primary_horizon",
        "secondary_horizons_are_context_not_substitutes_for_primary_horizon",
    ):
        if hypothesis.get(key) is not True:
            raise RuntimeError(f"validation hypothesis changed: {key}")
    if hypothesis.get("horizons_trading_days") != [21, 63, 126]:
        raise RuntimeError("validation horizons changed")
    if int(hypothesis.get("minimum_compared_group_support", -1)) != 20:
        raise RuntimeError("minimum compared-group support changed")
    if int(hypothesis.get("minimum_distinct_exposure_families_per_directional_state", -1)) != 2:
        raise RuntimeError("minimum exposure-family coverage changed")
    if int(hypothesis.get("primary_horizon_trading_days", -1)) != 63:
        raise RuntimeError("primary validation horizon changed")

    boundary = design["validation_boundary"]
    for key in (
        "new_unseen_validation_package_must_postdate_consumed_v1_v2_evidence",
        "new_unseen_validation_data_collection_requires_separate_authorization",
        "action_mapping_must_be_frozen_before_new_unseen_outcomes_are_inspected",
        "validation_outcomes_may_not_be_used_to_edit_this_mapping_without_new_version_and_governance_decision",
        "consumed_v1_v2_intervals_may_not_be_reused_as_unseen_validation",
        "overlapping_forward_windows_must_be_disclosed",
        "support_must_be_reported_by_vehicle_and_exposure_family",
    ):
        if boundary.get(key) is not True:
            raise RuntimeError(f"validation boundary changed: {key}")

    controls = design["controls"]
    if controls.get("v3_regime_definition_authorized") is not True or controls.get("v3_regime_definition_locked") is not True:
        raise RuntimeError("regime definition is not locked")
    if controls.get("action_mapping_design_authorized") is not True:
        raise RuntimeError("action mapping design is not authorized")
    for key in (
        "action_mapping_frozen",
        "new_validation_data_collection_authorized",
        "new_validation_outcome_inspection_authorized",
        "candidate_tactical_posture_authorized",
        "live_tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "native_source_query_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited downstream authority changed: {key}")

    if design.get("next_decision") != "CONSIDER_FREEZING_METALS_TACTICAL_POLICY_V3_ACTION_MAPPING":
        raise RuntimeError("unexpected next decision")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": design["design_id"],
        "source_regime_definition": design["source_regime_definition"],
        "source_classifier_rule_version": design["source_classifier_rule_version"],
        "mapping_version": mapping["mapping_version"],
        "candidate_action_state_count": 3,
        "trend_persistence_action": mapping["TREND_PERSISTENCE"]["candidate_action_state"],
        "mean_reversion_or_exhaustion_action": mapping["MEAN_REVERSION_OR_EXHAUSTION"]["candidate_action_state"],
        "neutral_or_uncertain_action": mapping["NEUTRAL_OR_UNCERTAIN"]["candidate_action_state"],
        "primary_validation_horizon_trading_days": int(hypothesis["primary_horizon_trading_days"]),
        "minimum_support_floor": int(hypothesis["minimum_compared_group_support"]),
        "minimum_exposure_family_count": int(hypothesis["minimum_distinct_exposure_families_per_directional_state"]),
        "action_mapping_frozen": False,
        "new_validation_data_collection_authorized": False,
        "new_validation_outcome_inspection_authorized": False,
        "tactical_posture_authorized": False,
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "next_decision": design["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
