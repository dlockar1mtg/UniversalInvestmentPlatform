from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_new_unseen_validation_authorization.json"


def load_auth() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_identity_and_sources() -> None:
    auth = load_auth()
    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-AUTHORIZATION-1"
    assert auth["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1"
    assert auth["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert auth["source_action_mapping_freeze_decision"] == "METALS-TACTICAL-POLICY-V3-ACTION-MAPPING-FREEZE-DECISION-1"
    assert auth["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1"


def test_unseen_interval_starts_after_consumed_evidence() -> None:
    interval = load_auth()["unseen_validation_interval"]
    assert interval["consumed_interval_end_date"] == "2023-08-21"
    assert interval["new_validation_history_start_date"] == "2023-08-22"
    assert interval["new_validation_history_end_date"] == "2026-08-24"
    assert interval["new_validation_label_interval_must_not_begin_before"] == "2023-08-22"
    assert interval["consumed_v1_v2_label_or_outcome_rows_may_not_enter_new_validation_results"] is True
    assert interval["earlier_certified_history_may_be_used_only_as_point_in_time_feature_warmup"] is True
    assert interval["warmup_rows_do_not_become_unseen_validation_observations"] is True


def test_collection_is_raw_close_outcome_blind_and_hash_first() -> None:
    collection = load_auth()["collection_authority"]
    assert collection["source_provider"] == "yfinance"
    assert collection["network_collection_authorized"] is True
    assert collection["required_auto_adjust"] is False
    assert collection["required_price_field"] == "close_usd"
    assert collection["required_price_semantics"] == "UNADJUSTED_CLOSE"
    assert collection["history_package_must_be_immutable_after_collection"] is True
    assert collection["package_hashes_required_before_any_classifier_or_outcome_execution"] is True
    assert collection["outcome_blind_collection_required"] is True


def test_vehicle_universe_and_reference_control_are_fixed() -> None:
    universe = load_auth()["vehicle_universe"]
    assert universe["opportunity_vehicles"] == ["COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]
    assert universe["reference_control_vehicle"] == "BIL"
    assert universe["vehicle_count"] == 11
    assert universe["opportunity_vehicle_count"] == 10
    assert universe["reference_control_count"] == 1
    assert universe["bil_is_reference_control_only"] is True
    assert universe["known_non_independent_groups"] == [["GLD", "IAU", "SGOL"], ["SIVR", "SLV"]]


def test_locked_validation_protocol_is_unchanged() -> None:
    protocol = load_auth()["locked_validation_protocol"]
    assert protocol["primary_horizon_trading_days"] == 63
    assert protocol["secondary_horizons_trading_days"] == [21, 126]
    assert protocol["minimum_compared_group_support"] == 20
    assert protocol["minimum_distinct_exposure_families_per_directional_state"] == 2
    assert protocol["all_three_primary_directional_checks_required"] is True
    assert protocol["supportive_median_return_should_exceed_defensive"] is True
    assert protocol["supportive_positive_return_rate_should_exceed_defensive"] is True
    assert protocol["supportive_mean_mae_should_be_less_negative_than_defensive"] is True
    assert protocol["secondary_horizons_cannot_substitute_for_primary_failure"] is True


def test_collection_does_not_authorize_outcome_inspection_or_live_use() -> None:
    auth = load_auth()
    boundaries = auth["governance_boundaries"]
    controls = auth["controls"]
    assert boundaries["validation_outcomes_may_not_be_calculated_or_inspected_during_collection"] is True
    assert boundaries["candidate_labels_may_not_be_evaluated_for_performance_during_collection"] is True
    assert boundaries["new_validation_package_must_be_frozen_and_hashed_before_outcome_inspection_authorization"] is True
    assert controls["new_validation_data_collection_authorized"] is True
    assert controls["new_validation_outcome_inspection_authorized"] is False
    assert controls["new_validation_result_authorized"] is False
    assert controls["candidate_tactical_posture_authorized"] is False
    assert controls["live_tactical_posture_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["model_retraining_authorized"] is False
    assert controls["automatic_execution_authorized"] is False


def test_required_outputs_and_next_decision_are_fixed() -> None:
    auth = load_auth()
    assert auth["required_collection_outputs"] == [
        "metals_v3_new_unseen_validation_history.jsonl",
        "coverage.json",
        "manifest.json",
    ]
    assert auth["next_decision"] == "COLLECT_AND_FREEZE_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_PACKAGE"
