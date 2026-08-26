from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "native_uranium_realized_outcome_derivation_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "native_uranium_realized_outcome_derivation_execution_authorization.json"

EXPECTED_OUTPUTS = {
    "native_uranium_realized_outcome_event_json",
    "forecast_state_outcome_alignment_csv",
    "forecast_state_outcome_alignment_json",
    "native_outcome_lineage_json",
    "independence_accounting_json",
    "derivation_invariant_checks_json",
    "derivation_summary_json",
}


def load_design():
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def load_auth():
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_identity_and_sources() -> None:
    design = load_design()
    auth = load_auth()
    assert auth["authorization_id"] == "METALS-NATIVE-URANIUM-REALIZED-OUTCOME-DERIVATION-EXECUTION-AUTHORIZATION-1"
    assert auth["source_design_id"] == design["design_id"]
    assert auth["source_design_head"] == "7e80a189f2731c2d11e22a0fa1d75a82226c9264"
    assert auth["source_reconstruction_id"] == design["source_reconstruction_id"]
    assert auth["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_authorized_scope_is_exact() -> None:
    scope = load_auth()["authorized_outcome_scope"]
    assert scope["asset_id"] == "METALS:COMMODITY:URANIUM"
    assert scope["source_authority"] == "eia"
    assert scope["forecast_state_count"] == 8
    assert scope["distinct_native_outcome_event_count"] == 1
    assert scope["effective_independent_outcome_n"] == 1
    assert scope["native_as_of_date"] == "2024-12-31"
    assert scope["target_outcome_date"] == "2025-12-31"
    assert scope["forecast_horizon_months"] == 12
    assert scope["forecast_horizon_anchor"] == "RECONSTRUCTED_NATIVE_AS_OF_DATE"
    assert scope["realized_return_formula"] == "future_native_value / as_of_native_value - 1"


def test_execution_behavior_all_true() -> None:
    behavior = load_auth()["required_execution_behavior"]
    assert len(behavior) == 16
    assert all(behavior.values())


def test_output_contract_matches_design_exactly() -> None:
    design = load_design()
    auth = load_auth()
    assert set(design["required_outputs_for_future_execution"]) == EXPECTED_OUTPUTS
    assert set(auth["required_outputs"]) == EXPECTED_OUTPUTS
    assert all(auth["required_outputs"].values())


def test_only_three_execution_boundaries_are_open() -> None:
    boundary = load_auth()["authorization_boundary"]
    assert len(boundary) == 17
    expected_open = {
        "native_uranium_realized_outcome_derivation_authorized",
        "hosted_read_only_access_authorized",
        "local_evidence_artifact_write_authorized",
    }
    observed_open = {key for key, value in boundary.items() if value is True}
    assert observed_open == expected_open


def test_downstream_authorities_remain_closed() -> None:
    boundary = load_auth()["authorization_boundary"]
    for key in (
        "historical_backtest_authorized",
        "candidate_policy_backtest_authorized",
        "final_action_policy_authorized",
        "final_action_selection_authorized",
        "recommendation_recompute_authorized",
        "forecast_refresh_authorized",
        "model_refresh_authorized",
        "database_write_authorized",
        "hosted_write_authorized",
        "runtime_change_authorized",
        "network_collection_authorized",
        "pr_authorized",
        "main_deploy_authorized",
        "allocation_or_execution_authorized",
    ):
        assert boundary[key] is False


def test_authorization_decisions() -> None:
    auth = load_auth()
    assert auth["authorization_decision"] == "AUTHORIZE_BOUNDED_NATIVE_URANIUM_REALIZED_OUTCOME_DERIVATION"
    assert auth["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_NATIVE_URANIUM_REALIZED_OUTCOME_DERIVATION"
