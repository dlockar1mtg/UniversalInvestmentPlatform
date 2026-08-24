from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "tactical_policy_walk_forward_evaluation_design.json"
SCRIPT = ROOT / "scripts" / "verify_metals_tactical_policy_walk_forward_evaluation_design.py"


def load_contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_walk_forward_design_locks_split_before_outcomes() -> None:
    contract = load_contract()
    grid = contract["evaluation_grid"]
    controls = contract["controls"]
    assert contract["design_id"] == "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-DESIGN-1"
    assert grid["walk_forward_step_observations"] == 5
    assert grid["forward_horizons_observations"] == [21, 63]
    assert grid["development_grid_points_per_asset"] == 53
    assert grid["holdout_grid_points_per_asset"] == 35
    assert grid["development_opportunity_grid_points"] == 530
    assert grid["holdout_opportunity_grid_points"] == 350
    assert controls["forward_outcome_calculation_authorized"] is False
    assert controls["historical_candidate_evaluation_authorized"] is False


def test_walk_forward_design_preserves_rule_lock_and_governance() -> None:
    contract = load_contract()
    rules = contract["interpretation_rules"]
    pass_rules = contract["candidate_pass_fail_rules"]
    controls = contract["controls"]
    assert rules["development_results_are_diagnostic_only"] is True
    assert rules["candidate_rules_may_not_change_after_development_results_without_starting_a_new_validation_cycle"] is True
    assert rules["holdout_results_are_final_for_this_candidate_version"] is True
    assert rules["overlapping_forward_windows_must_be_disclosed"] is True
    assert rules["duplicate_exposure_families_must_not_be_treated_as_independent_confirmation"] is True
    assert pass_rules["minimum_supported_holdout_observations_per_compared_group"] == 20
    assert pass_rules["if_minimum_group_support_not_met"] == "INCONCLUSIVE_NOT_PASS"
    assert pass_rules["passing_candidate_does_not_authorize_production_posture"] is True
    assert controls["candidate_threshold_change_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["cross_domain_rank_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False


def test_walk_forward_verifier_is_read_only() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    upper = text.upper()
    assert "INSERT INTO" not in upper
    assert "UPDATE " not in upper
    assert "DELETE FROM" not in upper
    assert "PSYCOPG" not in upper
    assert "DUCKDB.CONNECT" not in upper
    assert "NEXT_DECISION" not in upper or "next_decision" in text
