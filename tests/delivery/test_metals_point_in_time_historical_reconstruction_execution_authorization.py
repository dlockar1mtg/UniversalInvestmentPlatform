from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "point_in_time_historical_reconstruction_execution_authorization.json"
DESIGN_PATH = ROOT / "config" / "metals" / "point_in_time_historical_reconstruction_design.json"

EXPECTED_OUTPUTS = {
    "reconstructed_forecast_rows_json",
    "reconstructed_forecast_rows_csv",
    "cutoff_input_lineage_json",
    "point_in_time_invariant_checks_json",
    "reconstruction_coverage_json",
    "unavailable_cutoff_register_json",
    "reconstruction_summary_json",
}

EXPECTED_CUTOFFS = [
    "2024-12-31",
    "2025-01-31",
    "2025-02-28",
    "2025-03-31",
    "2025-04-30",
    "2025-05-31",
    "2025-06-30",
    "2025-07-31",
]


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_authorization_binds_certified_design() -> None:
    auth = load(AUTH_PATH)
    design = load(DESIGN_PATH)
    assert auth["authorization_id"] == "METALS-POINT-IN-TIME-HISTORICAL-RECONSTRUCTION-EXECUTION-AUTHORIZATION-1"
    assert auth["source_design_id"] == design["design_id"]
    assert auth["source_design_head"] == "c03eb42e42a295fcbcf9155c6e3fd5aee8c54987"
    assert auth["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_scope_is_exactly_bounded_uranium_12_month_cohort() -> None:
    scope = load(AUTH_PATH)["authorized_scope"]
    assert scope["candidate_cutoffs"] == EXPECTED_CUTOFFS
    assert scope["horizons_months"] == [12]
    assert scope["benchmark_cohort"] == ["METALS:COMMODITY:URANIUM"]
    assert scope["vehicle_context_series_count"] == 11
    assert scope["bil_role"] == "REFERENCE_CONTROL_ONLY"


def test_execution_behavior_is_closed_and_point_in_time_safe() -> None:
    behavior = load(AUTH_PATH)["required_execution_behavior"]
    assert len(behavior) == 16
    assert all(value is True for value in behavior.values())
    assert behavior["hosted_source_connection_must_be_read_only"] is True
    assert behavior["filter_every_benchmark_observation_to_observation_date_lte_cutoff"] is True
    assert behavior["filter_every_vehicle_observation_to_observation_date_lte_cutoff"] is True
    assert behavior["fail_if_any_input_observation_date_exceeds_cutoff"] is True
    assert behavior["do_not_substitute_vehicle_price_history_for_commodity_outcomes"] is True


def test_output_contract_exactly_matches_certified_design() -> None:
    auth = load(AUTH_PATH)
    design = load(DESIGN_PATH)
    outputs = auth["required_outputs"]
    assert set(outputs) == EXPECTED_OUTPUTS
    assert len(outputs) == 7
    assert all(value is True for value in outputs.values())
    assert set(design["required_outputs_for_future_execution"]) == EXPECTED_OUTPUTS


def test_only_reconstruction_read_and_local_evidence_write_are_open() -> None:
    boundary = load(AUTH_PATH)["authorization_boundary"]
    allowed_true = {
        "point_in_time_reconstruction_execution_authorized",
        "hosted_read_only_access_authorized",
        "local_evidence_artifact_write_authorized",
    }
    assert set(key for key, value in boundary.items() if value is True) == allowed_true
    assert all(value is False for key, value in boundary.items() if key not in allowed_true)


def test_no_outcome_backtest_policy_or_runtime_authority() -> None:
    boundary = load(AUTH_PATH)["authorization_boundary"]
    for key in (
        "realized_return_derivation_authorized",
        "historical_backtest_authorized",
        "candidate_policy_backtest_authorized",
        "final_action_policy_authorized",
        "final_action_selection_authorized",
        "recommendation_recompute_authorized",
        "forecast_refresh_authorized",
        "model_refresh_authorized",
        "hosted_write_authorized",
        "database_write_authorized",
        "runtime_change_authorized",
        "network_collection_authorized",
        "pr_authorized",
        "main_deploy_authorized",
        "allocation_or_execution_authorized",
    ):
        assert boundary[key] is False


def test_authorization_decision_and_next_step_are_exact() -> None:
    auth = load(AUTH_PATH)
    assert auth["authorization_decision"] == "AUTHORIZE_READ_ONLY_METALS_POINT_IN_TIME_HISTORICAL_RECONSTRUCTION"
    assert auth["next_decision"] == "EXECUTE_AND_CERTIFY_METALS_POINT_IN_TIME_HISTORICAL_RECONSTRUCTION"
