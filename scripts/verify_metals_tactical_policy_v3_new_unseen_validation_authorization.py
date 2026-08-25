from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_new_unseen_validation_authorization.json"
FREEZE_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_action_mapping_freeze_decision.json"
REGIME_LOCK_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_regime_definition_lock_decision.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    regime = json.loads(REGIME_LOCK_PATH.read_text(encoding="utf-8"))

    require(auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-AUTHORIZATION-1", "unexpected authorization id")
    require(auth["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1", "unexpected source regime definition")
    require(auth["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "unexpected classifier rule version")
    require(auth["source_action_mapping_freeze_decision"] == "METALS-TACTICAL-POLICY-V3-ACTION-MAPPING-FREEZE-DECISION-1", "unexpected action mapping freeze")
    require(auth["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", "unexpected action mapping version")

    require(freeze["scope_of_freeze"]["action_mapping_frozen"] is True, "action mapping is not frozen")
    require(freeze["scope_of_freeze"]["new_validation_outcome_inspection_authorized"] is False, "source freeze unexpectedly authorized outcome inspection")
    require(regime["controls"]["v3_regime_definition_locked"] is True, "regime definition is not locked")

    interval = auth["unseen_validation_interval"]
    require(interval["consumed_interval_end_date"] == "2023-08-21", "consumed interval end changed")
    require(interval["new_validation_history_start_date"] == "2023-08-22", "unexpected validation start")
    require(interval["new_validation_history_end_date"] == "2026-08-24", "unexpected validation end")
    require(interval["new_validation_label_interval_must_not_begin_before"] == "2023-08-22", "unexpected label boundary")
    require(interval["consumed_v1_v2_label_or_outcome_rows_may_not_enter_new_validation_results"] is True, "consumed evidence protection missing")
    require(interval["earlier_certified_history_may_be_used_only_as_point_in_time_feature_warmup"] is True, "warmup boundary missing")
    require(interval["warmup_rows_do_not_become_unseen_validation_observations"] is True, "warmup rows may become validation observations")

    collection = auth["collection_authority"]
    require(collection["source_provider"] == "yfinance", "unexpected provider")
    require(collection["network_collection_authorized"] is True, "collection not authorized")
    require(collection["required_auto_adjust"] is False, "auto_adjust must be false")
    require(collection["required_price_field"] == "close_usd", "raw close field changed")
    require(collection["required_price_semantics"] == "UNADJUSTED_CLOSE", "price semantics changed")
    require(collection["history_package_must_be_immutable_after_collection"] is True, "package immutability missing")
    require(collection["package_hashes_required_before_any_classifier_or_outcome_execution"] is True, "hash-before-execution requirement missing")
    require(collection["outcome_blind_collection_required"] is True, "collection must be outcome blind")

    universe = auth["vehicle_universe"]
    expected_opportunities = ["COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]
    require(universe["opportunity_vehicles"] == expected_opportunities, "opportunity universe changed")
    require(universe["reference_control_vehicle"] == "BIL", "BIL control changed")
    require(universe["vehicle_count"] == 11, "vehicle count changed")
    require(universe["opportunity_vehicle_count"] == 10, "opportunity vehicle count changed")
    require(universe["bil_is_reference_control_only"] is True, "BIL role changed")
    require(universe["known_non_independent_groups"] == [["GLD", "IAU", "SGOL"], ["SIVR", "SLV"]], "non-independent groups changed")

    protocol = auth["locked_validation_protocol"]
    require(protocol["primary_horizon_trading_days"] == 63, "primary horizon changed")
    require(protocol["secondary_horizons_trading_days"] == [21, 126], "secondary horizons changed")
    require(protocol["minimum_compared_group_support"] == 20, "support floor changed")
    require(protocol["minimum_distinct_exposure_families_per_directional_state"] == 2, "exposure-family floor changed")
    require(protocol["all_three_primary_directional_checks_required"] is True, "primary checks changed")
    require(protocol["secondary_horizons_cannot_substitute_for_primary_failure"] is True, "secondary horizon boundary changed")

    boundaries = auth["governance_boundaries"]
    for key in [
        "classifier_may_not_be_changed_during_collection",
        "action_mapping_may_not_be_changed_during_collection",
        "validation_thresholds_may_not_be_changed_during_collection",
        "validation_outcomes_may_not_be_calculated_or_inspected_during_collection",
        "candidate_labels_may_not_be_evaluated_for_performance_during_collection",
        "new_validation_package_must_be_frozen_and_hashed_before_outcome_inspection_authorization",
    ]:
        require(boundaries[key] is True, f"missing governance boundary: {key}")

    controls = auth["controls"]
    require(controls["v3_regime_definition_locked"] is True, "regime lock control changed")
    require(controls["action_mapping_frozen"] is True, "action mapping freeze control changed")
    require(controls["new_validation_data_collection_authorized"] is True, "collection authorization missing")
    require(controls["new_validation_outcome_inspection_authorized"] is False, "outcome inspection unexpectedly authorized")
    require(controls["new_validation_result_authorized"] is False, "validation result unexpectedly authorized")
    require(controls["candidate_tactical_posture_authorized"] is False, "candidate tactical posture unexpectedly authorized")
    require(controls["live_tactical_posture_authorized"] is False, "live tactical posture unexpectedly authorized")
    require(controls["production_database_write_authorized"] is False, "database write unexpectedly authorized")
    require(controls["presentation_activation_authorized"] is False, "presentation unexpectedly authorized")
    require(controls["model_retraining_authorized"] is False, "retraining unexpectedly authorized")
    require(controls["automatic_execution_authorized"] is False, "automatic execution unexpectedly authorized")

    require(auth["required_collection_outputs"] == ["metals_v3_new_unseen_validation_history.jsonl", "coverage.json", "manifest.json"], "required outputs changed")
    require(auth["next_decision"] == "COLLECT_AND_FREEZE_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_PACKAGE", "unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "validation_start_date": interval["new_validation_history_start_date"],
        "validation_end_date": interval["new_validation_history_end_date"],
        "source_provider": collection["source_provider"],
        "required_price_semantics": collection["required_price_semantics"],
        "vehicle_count": universe["vehicle_count"],
        "opportunity_vehicle_count": universe["opportunity_vehicle_count"],
        "reference_control_vehicle": universe["reference_control_vehicle"],
        "primary_validation_horizon_trading_days": protocol["primary_horizon_trading_days"],
        "minimum_support_floor": protocol["minimum_compared_group_support"],
        "minimum_exposure_family_count": protocol["minimum_distinct_exposure_families_per_directional_state"],
        "new_validation_data_collection_authorized": controls["new_validation_data_collection_authorized"],
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": controls["live_tactical_posture_authorized"],
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "next_decision": auth["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
