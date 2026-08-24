from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "tactical_policy_walk_forward_evaluation.json"
SCRIPT = ROOT / "scripts" / "evaluate_metals_tactical_policy_walk_forward.py"


def test_walk_forward_evaluation_authorization_exists() -> None:
    data = json.loads(AUTH.read_text(encoding="utf-8"))
    assert data["evaluation_id"] == "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-1"
    assert data["source_evaluation_design"] == "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-DESIGN-1"
    assert data["source_candidate_rule_design"] == "METALS-TACTICAL-POLICY-CANDIDATE-RULE-DESIGN-1"
    assert data["source_package_id"] == "metals-price-history-20260824"
    assert data["source_authority"] == "METALS-MARKET-HISTORY-1"


def test_only_historical_evaluation_is_authorized() -> None:
    controls = json.loads(AUTH.read_text(encoding="utf-8"))["controls"]
    assert controls["forward_outcome_calculation_authorized"] is True
    assert controls["historical_candidate_evaluation_authorized"] is True
    for key in (
        "candidate_threshold_change_authorized", "tactical_posture_authorized",
        "presentation_activation_authorized", "production_database_write_authorized",
        "native_source_query_authorized", "export_execution_authorized",
        "forecast_refresh_authorized", "model_retraining_authorized",
        "cross_domain_rank_authorized", "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        assert controls[key] is False


def test_locked_counts_are_preserved() -> None:
    data = json.loads(AUTH.read_text(encoding="utf-8"))
    assert data["expected_vehicle_count"] == 11
    assert data["expected_opportunity_vehicle_count"] == 10
    assert data["expected_reference_control_count"] == 1
    assert data["expected_history_observations_per_asset"] == 753
    assert data["expected_grid_points_per_asset"] == 88
    assert data["expected_development_grid_points_per_asset"] == 53
    assert data["expected_holdout_grid_points_per_asset"] == 35
    assert data["expected_development_opportunity_points"] == 530
    assert data["expected_holdout_opportunity_points"] == 350


def test_evaluator_locks_semantics_and_governance() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for token in (
        "candidate_validation_result",
        "minimum_group_support_met",
        "INCONCLUSIVE",
        "overlapping_forward_windows_disclosed",
        "duplicate_exposure_families_not_independent_confirmation",
        "tactical_posture_authorized",
        "production_database_write_executed",
        "native_source_query_executed",
        "candidate_thresholds_changed",
    ):
        assert token in text
    assert "psycopg" not in text
    assert "duckdb" not in text.lower()


def test_reference_control_never_gets_opportunity_posture() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'posture = "REFERENCE_CONTROL"' in text
    assert 'role = "REFERENCE_CONTROL" if asset_id == REFERENCE else "TACTICAL_OPPORTUNITY"' in text
