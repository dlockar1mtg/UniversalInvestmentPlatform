from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_new_unseen_validation_outcome_inspection_authorization.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_new_unseen_validation_outcome_inspection_authorization.py"


def load_auth() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_identity_and_frozen_sources() -> None:
    auth = load_auth()
    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-OUTCOME-INSPECTION-AUTHORIZATION-1"
    assert auth["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1"
    assert auth["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert auth["source_action_mapping_freeze_decision"] == "METALS-TACTICAL-POLICY-V3-ACTION-MAPPING-FREEZE-DECISION-1"
    assert auth["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1"


def test_frozen_unseen_package_is_bound_to_exact_hashes() -> None:
    package = load_auth()["frozen_unseen_package"]
    assert package["package_id"] == "metals-v3-new-unseen-validation-20230822-20260824"
    assert package["validation_start_date"] == "2023-08-22"
    assert package["validation_end_date"] == "2026-08-24"
    assert package["row_count"] == 8294
    assert package["common_observation_count"] == 754
    assert package["history_sha256"] == "597a979ad5b5c031b4c15b84e3d8b23389c780e9a3fc5a19bd1b06ca4b61a6d5"
    assert package["coverage_sha256"] == "3de3cb2d21ff247f78e210372bc5505bf13d5b3fd2475260fc84cfb514d91c7e"
    assert package["manifest_sha256"] == "69ed6ff5324f148734a8b84e672e028fcd2e17893bfac4b4c402063916dcf205"
    assert package["package_frozen"] is True
    assert package["package_outcome_blind_at_freeze"] is True


def test_consumed_v2_history_is_warmup_only() -> None:
    warmup = load_auth()["point_in_time_warmup_authority"]
    assert warmup["package_id"] == "metals-v2-validation-history-20191204-20230821"
    assert warmup["warmup_end_date"] == "2023-08-21"
    assert warmup["may_be_used_only_for_point_in_time_feature_warmup"] is True
    assert warmup["warmup_rows_may_not_be_validation_label_rows"] is True
    assert warmup["warmup_rows_may_not_be_validation_outcome_rows"] is True
    assert warmup["v1_v2_intervals_remain_consumed"] is True


def test_label_ledger_must_be_frozen_before_outcomes() -> None:
    seq = load_auth()["authorized_execution_sequence"]
    assert seq["step_1_verify_all_frozen_input_hashes"] is True
    assert seq["step_2_construct_point_in_time_features_using_only_information_available_through_each_label_date"] is True
    assert seq["step_3_assign_locked_regime_labels_only_on_or_after_2023_08_22"] is True
    assert seq["step_4_apply_frozen_action_mapping"] is True
    assert seq["step_5_persist_and_hash_label_ledger_before_forward_outcome_calculation"] is True
    assert seq["step_6_calculate_predeclared_forward_outcomes_from_frozen_history"] is True
    assert seq["step_7_evaluate_locked_primary_and_secondary_validation_checks"] is True
    assert seq["label_ledger_may_not_change_after_forward_outcomes_are_calculated"] is True
    assert seq["network_query_during_execution_authorized"] is False
    assert seq["source_data_refresh_during_execution_authorized"] is False


def test_primary_validation_protocol_remains_fail_closed() -> None:
    protocol = load_auth()["locked_validation_protocol"]
    assert protocol["primary_horizon_trading_days"] == 63
    assert protocol["secondary_horizons_trading_days"] == [21, 126]
    assert protocol["minimum_compared_group_support"] == 20
    assert protocol["minimum_distinct_exposure_families_per_directional_state"] == 2
    assert protocol["supportive_median_return_should_exceed_defensive"] is True
    assert protocol["supportive_positive_return_rate_should_exceed_defensive"] is True
    assert protocol["supportive_mean_mae_should_be_less_negative_than_defensive"] is True
    assert protocol["all_three_primary_directional_checks_required"] is True
    assert protocol["secondary_horizons_cannot_substitute_for_primary_failure"] is True
    assert protocol["insufficient_primary_support_is_fail_closed"] is True


def test_authorization_does_not_authorize_live_use_or_writes() -> None:
    controls = load_auth()["controls"]
    assert controls["new_validation_package_frozen"] is True
    assert controls["new_validation_outcome_inspection_authorized"] is True
    assert controls["new_validation_result_authorized"] is True
    assert controls["network_collection_authorized"] is False
    assert controls["source_refresh_authorized"] is False
    assert controls["candidate_tactical_posture_authorized"] is False
    assert controls["live_tactical_posture_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["model_retraining_authorized"] is False
    assert controls["automatic_execution_authorized"] is False


def test_result_governance_prevents_post_hoc_rescue() -> None:
    result = load_auth()["result_governance"]
    assert result["primary_result_pass_requires_all_primary_support_and_directional_checks"] is True
    assert result["primary_result_failure_must_remain_failure"] is True
    assert result["primary_result_inconclusive_must_remain_inconclusive"] is True
    assert result["secondary_results_may_not_rescue_primary_failure_or_inconclusive_result"] is True
    assert result["successful_validation_does_not_itself_authorize_live_tactical_posture"] is True
    assert result["separate_post_validation_live_use_decision_required"] is True


def test_verifier_is_static_read_only_and_next_decision_is_execution() -> None:
    text = VERIFIER_PATH.read_text(encoding="utf-8")
    assert "yfinance" not in text
    assert ".write_text(" not in text
    assert "open(\"w\"" not in text
    assert load_auth()["next_decision"] == "EXECUTE_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_OUTCOME_INSPECTION"
