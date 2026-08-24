from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_validation_evaluation_design.json"


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    package = contract["validation_package"]
    grid = contract["evaluation_grid"]
    features = contract["historical_feature_contract"]
    candidate = contract["locked_candidate"]
    outcomes = contract["required_outcomes"]
    checks = contract["final_validation_checks"]
    interpretation = contract["interpretation_constraints"]
    controls = contract["controls"]

    assert contract["design_id"] == "METALS-TACTICAL-POLICY-V2-VALIDATION-EVALUATION-DESIGN-1"
    assert contract["source_current_price_semantic_review"] == "METALS-CURRENT-PRICE-SEMANTIC-REVIEW-1"
    assert contract["source_validation_history_package_review"] == "METALS-TACTICAL-POLICY-V2-VALIDATION-HISTORY-PACKAGE-REVIEW-1"
    assert contract["source_candidate_rule_design"] == "METALS-TACTICAL-POLICY-V2-CANDIDATE-RULE-DESIGN-1"

    assert package["package_id"] == "metals-v2-validation-history-20191204-20230821"
    assert package["common_start_date"] == "2019-12-04"
    assert package["common_end_date"] == "2023-08-21"
    assert int(package["common_observation_count"]) == 934
    assert int(package["vehicle_count"]) == 11
    assert int(package["opportunity_vehicle_count"]) == 10
    assert package["reference_control_asset_id"] == "metals:vehicle:BIL"

    assert int(grid["minimum_history_observations"]) == 252
    assert int(grid["walk_forward_step_observations"]) == 5
    assert grid["forward_horizons_observations"] == [21, 63]
    assert int(grid["first_candidate_index_zero_based"]) == 251
    assert int(grid["last_forward_evaluable_index_zero_based"]) == 870
    assert int(grid["expected_grid_points_per_vehicle"]) == 124
    assert int(grid["expected_total_grid_points"]) == 1364
    assert int(grid["expected_opportunity_grid_points"]) == 1240
    assert int(grid["expected_reference_control_grid_points"]) == 124
    assert grid["entire_grid_is_final_unseen_validation"] is True
    assert grid["development_tuning_on_validation_interval_prohibited"] is True

    assert len(features["required_inputs"]) == 7
    assert features["feature_price_basis"] == "ADJUSTED_CLOSE_WHEN_AVAILABLE_ELSE_CLOSE"
    assert features["forward_return_price_basis"] == "ADJUSTED_CLOSE_WHEN_AVAILABLE_ELSE_CLOSE"
    assert features["point_in_time_only"] is True
    assert features["future_values_prohibited_in_candidate_inputs"] is True

    assert candidate["postures"] == ["ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"]
    assert candidate["constructive_group"] == ["ACCUMULATE", "HOLD"]
    assert candidate["defensive_group"] == ["REDUCE", "AVOID"]
    assert candidate["neutral_group"] == ["WATCH"]
    assert int(candidate["minimum_compared_group_support"]) == 20
    assert candidate["candidate_rules_may_not_change_during_or_after_validation"] is True
    assert candidate["thresholds_may_not_change_during_or_after_validation"] is True

    assert outcomes["forward_return_pct"] is True
    assert outcomes["maximum_adverse_excursion_pct"] is True
    assert outcomes["maximum_favorable_excursion_pct"] is True
    assert outcomes["outcomes_use_future_observations_only"] is True

    assert checks["constructive_63d_median_return_gt_defensive"] is True
    assert checks["constructive_63d_positive_return_rate_gt_defensive"] is True
    assert checks["defensive_63d_mean_mae_more_negative_than_constructive"] is True
    assert checks["holdout_posture_change_rate_lte_0_50"] is True
    assert checks["minimum_group_support_met"] is True
    assert checks["no_semantic_or_governance_violation"] is True
    assert checks["all_checks_required_for_pass"] is True
    assert checks["insufficient_group_support_result"] == "INCONCLUSIVE"
    assert checks["failed_directional_or_behavior_check_result"] == "FAIL"
    assert checks["passing_result"] == "PASS"

    assert interpretation["validation_interval_was_unseen_when_v2_rules_locked"] is True
    assert interpretation["validation_interval_is_consumed_once_evaluation_executes"] is True
    assert interpretation["overlapping_forward_windows_must_be_disclosed"] is True
    assert interpretation["vehicle_cluster_dependence_must_be_disclosed"] is True
    assert interpretation["passing_candidate_does_not_itself_authorize_live_tactical_postures"] is True

    assert controls["validation_evaluation_design_authorized"] is True
    assert controls["validation_outcome_calculation_authorized"] is False
    assert controls["historical_candidate_evaluation_authorized"] is False
    assert controls["new_validation_outcome_inspection_authorized"] is False
    assert controls["candidate_rule_change_authorized"] is False
    assert controls["candidate_threshold_change_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["native_source_query_authorized"] is False
    assert controls["package_regeneration_authorized"] is False
    assert controls["forecast_refresh_authorized"] is False
    assert controls["model_retraining_authorized"] is False
    assert controls["cross_domain_rank_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": contract["design_id"],
        "source_current_price_semantic_review": contract["source_current_price_semantic_review"],
        "source_validation_history_package_review": contract["source_validation_history_package_review"],
        "source_candidate_rule_design": contract["source_candidate_rule_design"],
        "package_id": package["package_id"],
        "common_start_date": package["common_start_date"],
        "common_end_date": package["common_end_date"],
        "common_observation_count": package["common_observation_count"],
        "vehicle_count": package["vehicle_count"],
        "opportunity_vehicle_count": package["opportunity_vehicle_count"],
        "reference_control_count": 1,
        "required_historical_input_count": len(features["required_inputs"]),
        "walk_forward_step_observations": grid["walk_forward_step_observations"],
        "forward_horizons_observations": grid["forward_horizons_observations"],
        "expected_grid_points_per_vehicle": grid["expected_grid_points_per_vehicle"],
        "expected_total_grid_points": grid["expected_total_grid_points"],
        "expected_opportunity_grid_points": grid["expected_opportunity_grid_points"],
        "expected_reference_control_grid_points": grid["expected_reference_control_grid_points"],
        "entire_grid_is_final_unseen_validation": grid["entire_grid_is_final_unseen_validation"],
        "corrected_downside_validation_direction_locked": checks["defensive_63d_mean_mae_more_negative_than_constructive"],
        "minimum_compared_group_support": candidate["minimum_compared_group_support"],
        "candidate_rules_locked": True,
        "candidate_thresholds_locked": True,
        "validation_outcomes_calculated": False,
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "historical_candidate_evaluation_authorized": controls["historical_candidate_evaluation_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "production_database_write_executed": False,
        "native_source_query_executed": False,
        "package_regeneration_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": controls["cross_domain_rank_authorized"],
        "allocation_policy_authorized": controls["allocation_policy_authorized"],
        "automatic_execution_authorized": controls["automatic_execution_authorized"],
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
