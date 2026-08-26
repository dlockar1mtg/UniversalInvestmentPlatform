from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "point_in_time_historical_reconstruction_design.json"


def _design() -> dict[str, object]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_design_identity_and_source_binding():
    design = _design()
    assert design["design_id"] == "METALS-POINT-IN-TIME-HISTORICAL-RECONSTRUCTION-DESIGN-1"
    assert design["source_governed_head"] == "8e1f9f47029ec6790094fdfac991e2fe8df7e00a"
    assert design["source_feasibility_finding"] == "HOSTED_POINT_IN_TIME_RECONSTRUCTION_FEASIBLE_FOR_BOUNDED_12_MONTH_URANIUM_COHORT"


def test_feasibility_counts_are_bound():
    findings = _design()["certified_feasibility_findings"]
    assert findings["hosted_benchmark_series_count"] == 9
    assert findings["hosted_benchmark_row_count"] == 18
    assert findings["hosted_vehicle_series_count"] == 11
    assert findings["hosted_vehicle_row_count"] == 8426
    assert findings["benchmark_backfilled_row_count"] == 18
    assert findings["vehicle_backfilled_row_count"] == 8316
    assert findings["usable_native_cutoff_count"] == 8
    assert findings["only_mature_native_horizon_months"] == [12]


def test_scope_is_bounded_to_supported_cutoffs_and_uranium():
    scope = _design()["reconstruction_scope"]
    assert scope["candidate_cutoffs"] == [
        "2024-12-31",
        "2025-01-31",
        "2025-02-28",
        "2025-03-31",
        "2025-04-30",
        "2025-05-31",
        "2025-06-30",
        "2025-07-31",
    ]
    assert scope["authorized_design_horizons_months"] == [12]
    assert scope["benchmark_cohort"] == ["METALS:COMMODITY:URANIUM"]
    assert scope["vehicle_context_series_count"] == 11
    assert scope["bil_role"] == "REFERENCE_CONTROL_ONLY"


def test_point_in_time_rules_are_all_true():
    rules = _design()["required_point_in_time_rules"]
    assert len(rules) == 16
    assert all(value is True for value in rules.values())
    assert rules["filter_every_benchmark_observation_to_observation_date_lte_cutoff"] is True
    assert rules["filter_every_vehicle_observation_to_observation_date_lte_cutoff"] is True
    assert rules["fail_if_any_input_observation_date_exceeds_cutoff"] is True
    assert rules["do_not_use_collected_at_utc_as_historical_availability_proof"] is True


def test_outcomes_remain_separately_authorized():
    constraints = _design()["historical_outcome_constraints"]
    assert len(constraints) == 6
    assert all(value is True for value in constraints.values())
    assert constraints["reconstruction_does_not_itself_authorize_realized_outcome_derivation"] is True
    assert constraints["native_commodity_outcome_authority_required_before_commodity_backtest"] is True
    assert constraints["vehicle_context_is_feature_evidence_not_commodity_outcome_proxy"] is True


def test_required_future_outputs_are_exact():
    outputs = _design()["required_outputs_for_future_execution"]
    assert set(outputs) == {
        "reconstructed_forecast_rows_json",
        "reconstructed_forecast_rows_csv",
        "cutoff_input_lineage_json",
        "point_in_time_invariant_checks_json",
        "reconstruction_coverage_json",
        "unavailable_cutoff_register_json",
        "reconstruction_summary_json",
    }
    assert all(value is True for value in outputs.values())


def test_all_execution_boundaries_remain_closed():
    boundaries = _design()["boundaries"]
    assert boundaries
    assert all(value is False for value in boundaries.values())


def test_next_decision_is_only_execution_authorization_consideration():
    design = _design()
    assert design["design_decision"] == "APPROVE_METALS_POINT_IN_TIME_HISTORICAL_RECONSTRUCTION_DESIGN_FOR_EXECUTION_AUTHORIZATION_CONSIDERATION"
    assert design["next_decision"] == "AUTHORIZE_READ_ONLY_METALS_POINT_IN_TIME_HISTORICAL_RECONSTRUCTION"
