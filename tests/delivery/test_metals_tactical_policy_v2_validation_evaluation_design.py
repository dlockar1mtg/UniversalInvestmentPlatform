import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "tactical_policy_v2_validation_evaluation_design.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v2_validation_evaluation_design.py"


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_unseen_validation_package_and_grid_are_locked():
    contract = load_contract()
    package = contract["validation_package"]
    grid = contract["evaluation_grid"]
    assert package["package_id"] == "metals-v2-validation-history-20191204-20230821"
    assert package["common_start_date"] == "2019-12-04"
    assert package["common_end_date"] == "2023-08-21"
    assert package["common_observation_count"] == 934
    assert grid["minimum_history_observations"] == 252
    assert grid["walk_forward_step_observations"] == 5
    assert grid["forward_horizons_observations"] == [21, 63]
    assert grid["expected_grid_points_per_vehicle"] == 124
    assert grid["expected_opportunity_grid_points"] == 1240
    assert grid["expected_reference_control_grid_points"] == 124
    assert grid["entire_grid_is_final_unseen_validation"] is True
    assert grid["development_tuning_on_validation_interval_prohibited"] is True


def test_feature_and_return_basis_are_explicit():
    features = load_contract()["historical_feature_contract"]
    assert len(features["required_inputs"]) == 7
    assert features["feature_price_basis"] == "ADJUSTED_CLOSE_WHEN_AVAILABLE_ELSE_CLOSE"
    assert features["forward_return_price_basis"] == "ADJUSTED_CLOSE_WHEN_AVAILABLE_ELSE_CLOSE"
    assert features["point_in_time_only"] is True
    assert features["future_values_prohibited_in_candidate_inputs"] is True


def test_candidate_rules_and_support_floor_remain_locked():
    candidate = load_contract()["locked_candidate"]
    assert candidate["constructive_group"] == ["ACCUMULATE", "HOLD"]
    assert candidate["defensive_group"] == ["REDUCE", "AVOID"]
    assert candidate["neutral_group"] == ["WATCH"]
    assert candidate["minimum_compared_group_support"] == 20
    assert candidate["candidate_rules_may_not_change_during_or_after_validation"] is True
    assert candidate["thresholds_may_not_change_during_or_after_validation"] is True


def test_corrected_downside_check_is_locked():
    checks = load_contract()["final_validation_checks"]
    assert checks["constructive_63d_median_return_gt_defensive"] is True
    assert checks["constructive_63d_positive_return_rate_gt_defensive"] is True
    assert checks["defensive_63d_mean_mae_more_negative_than_constructive"] is True
    assert checks["holdout_posture_change_rate_lte_0_50"] is True
    assert checks["minimum_group_support_met"] is True
    assert checks["all_checks_required_for_pass"] is True
    assert checks["insufficient_group_support_result"] == "INCONCLUSIVE"
    assert checks["failed_directional_or_behavior_check_result"] == "FAIL"


def test_design_does_not_consume_validation_outcomes():
    controls = load_contract()["controls"]
    assert controls["validation_evaluation_design_authorized"] is True
    assert controls["validation_outcome_calculation_authorized"] is False
    assert controls["historical_candidate_evaluation_authorized"] is False
    assert controls["new_validation_outcome_inspection_authorized"] is False
    assert controls["candidate_rule_change_authorized"] is False
    assert controls["candidate_threshold_change_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["production_database_write_authorized"] is False


def test_verifier_has_no_market_data_or_evaluation_engine_imports():
    text = VERIFIER.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert "pandas" not in imported_roots
    assert "numpy" not in imported_roots
    assert "yfinance" not in imported_roots
    lowered = text.lower()
    assert ".pct_change(" not in lowered
    assert ".rolling(" not in lowered
    assert "yf.download(" not in lowered


def test_next_decision_authorizes_evaluation_not_live_posture():
    contract = load_contract()
    assert contract["next_decision"] == "AUTHORIZE_METALS_TACTICAL_POLICY_V2_VALIDATION_EVALUATION"
