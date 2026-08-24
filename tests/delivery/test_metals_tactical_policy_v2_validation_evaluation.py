import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "tactical_policy_v2_validation_evaluation.json"
SCRIPT = ROOT / "scripts" / "evaluate_metals_tactical_policy_v2_validation.py"
RULE = ROOT / "config" / "metals" / "tactical_policy_v2_candidate_rule_design.json"
DESIGN = ROOT / "config" / "metals" / "tactical_policy_v2_validation_evaluation_design.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_authority_is_exactly_v2_final_validation():
    auth = load(AUTH)
    assert auth["evaluation_id"] == "METALS-TACTICAL-POLICY-V2-VALIDATION-EVALUATION-1"
    assert auth["source_design"] == "METALS-TACTICAL-POLICY-V2-VALIDATION-EVALUATION-DESIGN-1"
    assert auth["source_candidate_rule_design"] == "METALS-TACTICAL-POLICY-V2-CANDIDATE-RULE-DESIGN-1"
    assert auth["package_id"] == "metals-v2-validation-history-20191204-20230821"
    assert auth["expected_common_observation_count"] == 934
    assert auth["expected_grid_points_per_vehicle"] == 124
    assert auth["expected_total_grid_points"] == 1364
    assert auth["expected_opportunity_grid_points"] == 1240
    assert auth["expected_reference_control_grid_points"] == 124


def test_only_validation_consumption_is_authorized():
    controls = load(AUTH)["controls"]
    assert controls["validation_outcome_calculation_authorized"] is True
    assert controls["historical_candidate_evaluation_authorized"] is True
    assert controls["new_validation_outcome_inspection_authorized"] is True
    for key in (
        "candidate_rule_change_authorized", "candidate_threshold_change_authorized",
        "tactical_posture_authorized", "presentation_activation_authorized",
        "production_database_write_authorized", "native_source_query_authorized",
        "package_regeneration_authorized", "forecast_refresh_authorized",
        "model_retraining_authorized", "cross_domain_rank_authorized",
        "allocation_policy_authorized", "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        assert controls[key] is False


def test_candidate_rules_and_corrected_downside_direction_are_locked():
    rule = load(RULE)
    design = load(DESIGN)
    assert rule["validation_requirements"]["minimum_compared_group_support"] == 20
    assert rule["validation_requirements"]["defensive_63d_mean_maximum_adverse_excursion_must_be_more_negative_than_constructive"] is True
    assert design["final_validation_checks"]["defensive_63d_mean_mae_more_negative_than_constructive"] is True
    assert design["locked_candidate"]["candidate_rules_may_not_change_during_or_after_validation"] is True
    assert design["locked_candidate"]["thresholds_may_not_change_during_or_after_validation"] is True


def test_evaluator_uses_v2_rule_keys_and_correct_mae_comparison():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'rule["v2_candidate_signal_rules"]' in text
    assert 'rule["v2_candidate_score_mapping"]' in text
    assert 'float(defensive_63["mean_maximum_adverse_excursion_pct"]) < float(constructive_63["mean_maximum_adverse_excursion_pct"])' in text
    assert "defensive_63d_mean_mae_no_worse_than_constructive" not in text


def test_evaluator_has_no_network_or_database_imports():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for prohibited in ("yfinance", "requests", "httpx", "duckdb", "psycopg", "sqlalchemy"):
        assert prohibited not in imported


def test_evaluator_is_fail_closed_against_reusing_same_output_path():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "if output_path.exists():" in text
    assert "may not be overwritten" in text
    assert '"validation_interval_consumed": True' in text


def test_result_semantics_are_locked():
    semantics = load(AUTH)["result_semantics"]
    assert semantics["minimum_group_support_failure"] == "INCONCLUSIVE"
    assert semantics["directional_or_behavior_check_failure"] == "FAIL"
    assert semantics["all_required_checks_pass"] == "PASS"
    assert semantics["passing_result_does_not_authorize_live_tactical_postures"] is True
    assert semantics["validation_interval_consumed_once_evaluation_executes"] is True


def test_pass_does_not_authorize_live_tactical_posture():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"tactical_posture_authorized": False' in text
    assert '"presentation_activation_executed": False' in text
    assert '"automatic_execution_authorized": False' in text


def test_next_decisions_require_post_evaluation_review():
    decisions = load(AUTH)["next_decision_by_result"]
    assert decisions["PASS"] == "REVIEW_METALS_TACTICAL_POLICY_V2_POLICY_AUTHORITY"
    assert decisions["FAIL"] == "REVIEW_METALS_TACTICAL_POLICY_V2_FAILED_VALIDATION"
    assert decisions["INCONCLUSIVE"] == "REVIEW_METALS_TACTICAL_POLICY_V2_INCONCLUSIVE_VALIDATION"
