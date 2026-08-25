from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "config" / "metals" / "tactical_policy_v3_action_mapping_freeze_decision.json"
DESIGN = ROOT / "config" / "metals" / "tactical_policy_v3_action_mapping_design.json"
LOCK = ROOT / "config" / "metals" / "tactical_policy_v3_regime_definition_lock_decision.json"


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> int:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8"))

    if decision.get("decision_id") != "METALS-TACTICAL-POLICY-V3-ACTION-MAPPING-FREEZE-DECISION-1":
        fail("unexpected action-mapping freeze decision id")
    if decision.get("source_action_mapping_design") != design.get("design_id"):
        fail("freeze decision is not bound to action-mapping design")
    if decision.get("source_mapping_version") != design.get("candidate_action_mapping", {}).get("mapping_version"):
        fail("mapping version changed")
    if decision.get("source_regime_definition") != lock.get("locked_regime_definition", {}).get("definition_id"):
        fail("regime definition changed")
    if decision.get("source_classifier_rule_version") != lock.get("locked_regime_definition", {}).get("classifier_rule_version"):
        fail("classifier rule version changed")
    if decision.get("source_label_ledger_sha256") != lock.get("source_label_ledger_sha256"):
        fail("label-ledger binding changed")

    mapping = decision.get("frozen_action_mapping", {})
    if mapping.get("mapping_version") != "METALS-V3-ACTION-MAPPING-1":
        fail("unexpected frozen mapping version")
    if mapping.get("TREND_PERSISTENCE") != "TACTICAL_SUPPORTIVE":
        fail("unexpected trend-persistence action")
    if mapping.get("MEAN_REVERSION_OR_EXHAUSTION") != "TACTICAL_DEFENSIVE":
        fail("unexpected mean-reversion/exhaustion action")
    if mapping.get("NEUTRAL_OR_UNCERTAIN") != "NO_TACTICAL_OVERLAY":
        fail("unexpected neutral action")
    if mapping.get("mapping_is_ordinal_not_position_sizing") is not True:
        fail("mapping scope changed")
    if mapping.get("mapping_does_not_authorize_buy_sell_or_trade_execution") is not True:
        fail("trade boundary changed")
    if mapping.get("neutral_or_uncertain_remains_fail_closed") is not True:
        fail("neutral fail-closed control changed")

    hypothesis = decision.get("frozen_unseen_validation_hypothesis", {})
    if int(hypothesis.get("primary_horizon_trading_days", -1)) != 63:
        fail("primary horizon changed")
    if list(hypothesis.get("secondary_horizons_trading_days", [])) != [21, 126]:
        fail("secondary horizons changed")
    if int(hypothesis.get("minimum_compared_group_support", -1)) != 20:
        fail("support floor changed")
    if int(hypothesis.get("minimum_distinct_exposure_families_per_directional_state", -1)) != 2:
        fail("exposure-family floor changed")
    for key in (
        "supportive_median_return_should_exceed_defensive",
        "supportive_positive_return_rate_should_exceed_defensive",
        "supportive_mean_mae_should_be_less_negative_than_defensive",
        "all_three_directional_checks_required_at_primary_horizon",
        "secondary_horizons_are_context_not_substitutes_for_primary_horizon",
        "overlapping_forward_windows_must_be_disclosed",
        "support_must_be_reported_by_vehicle_and_exposure_family",
    ):
        if hypothesis.get(key) is not True:
            fail(f"frozen validation hypothesis control changed: {key}")

    boundary = decision.get("validation_boundary", {})
    for key in (
        "action_mapping_frozen_before_new_unseen_validation_outcome_inspection",
        "new_unseen_validation_package_must_postdate_consumed_v1_v2_evidence",
        "consumed_v1_v2_intervals_may_not_be_reused_as_unseen_validation",
        "mapping_may_not_be_changed_after_new_unseen_validation_outcomes_are_inspected_without_new_version_and_governance_decision",
        "classifier_may_not_be_changed_after_new_unseen_validation_outcomes_are_inspected_without_new_version_and_governance_decision",
        "new_validation_data_collection_requires_separate_authorization",
        "new_validation_outcome_inspection_requires_separate_authorization",
    ):
        if boundary.get(key) is not True:
            fail(f"validation boundary changed: {key}")

    scope = decision.get("scope_of_freeze", {})
    if scope.get("v3_regime_definition_authorized") is not True:
        fail("regime definition lost authority")
    if scope.get("v3_regime_definition_locked") is not True:
        fail("regime definition lost lock")
    if scope.get("action_mapping_design_authorized") is not True:
        fail("action-mapping design authority changed")
    if scope.get("action_mapping_frozen") is not True:
        fail("action mapping is not frozen")
    for key in (
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
        if scope.get(key) is not False:
            fail(f"unauthorized scope enabled: {key}")

    if decision.get("next_decision") != "DESIGN_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_AUTHORIZATION":
        fail("unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "decision_id": decision["decision_id"],
        "source_action_mapping_design": decision["source_action_mapping_design"],
        "mapping_version": mapping["mapping_version"],
        "trend_persistence_action": mapping["TREND_PERSISTENCE"],
        "mean_reversion_or_exhaustion_action": mapping["MEAN_REVERSION_OR_EXHAUSTION"],
        "neutral_or_uncertain_action": mapping["NEUTRAL_OR_UNCERTAIN"],
        "primary_validation_horizon_trading_days": hypothesis["primary_horizon_trading_days"],
        "minimum_support_floor": hypothesis["minimum_compared_group_support"],
        "minimum_exposure_family_count": hypothesis["minimum_distinct_exposure_families_per_directional_state"],
        "action_mapping_frozen": scope["action_mapping_frozen"],
        "new_validation_data_collection_authorized": scope["new_validation_data_collection_authorized"],
        "new_validation_outcome_inspection_authorized": scope["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": scope["live_tactical_posture_authorized"],
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "next_decision": decision["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
