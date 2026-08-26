from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "final_decision_arbitration_with_forward_validation_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "final_decision_arbitration_implementation_authorization.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_identity_and_source_binding():
    design = load(DESIGN_PATH)
    auth = load(AUTH_PATH)
    assert auth["authorization_id"] == "METALS-FINAL-DECISION-ARBITRATION-IMPLEMENTATION-AUTHORIZATION-1"
    assert auth["source_design_id"] == design["design_id"]
    assert auth["source_design_head"] == "d52932bbc876da559b4565e6056b42302bbfe9a6"
    assert auth["source_database_sha256"] == design["source_database_sha256"]


def test_policy_label_and_actions_match_design_exactly():
    design = load(DESIGN_PATH)
    auth = load(AUTH_PATH)
    assert auth["policy_authority_label"] == "POLICY_DRIVEN_PENDING_FORWARD_EMPIRICAL_VALIDATION"
    assert auth["policy_authority_label"] == design["arbitration_policy"]["policy_authority_label"]
    assert auth["authorized_current_asset_actions"] == design["current_asset_action_design"]
    assert len(auth["authorized_current_asset_actions"]) == 12
    assert "DECISION_CONFLICT" not in auth["authorized_current_asset_actions"].values()


def test_exact_current_actions():
    auth = load(AUTH_PATH)
    assert auth["authorized_current_asset_actions"] == {
        "metals:commodity:gold": "HOLD",
        "metals:commodity:uranium": "HOLD",
        "metals:vehicle:BIL": "REFERENCE_CONTROL",
        "metals:vehicle:COPX": "HOLD",
        "metals:vehicle:CPER": "HOLD",
        "metals:vehicle:GLD": "WATCH",
        "metals:vehicle:IAU": "WATCH",
        "metals:vehicle:PPLT": "WATCH",
        "metals:vehicle:SGOL": "WATCH",
        "metals:vehicle:SIVR": "WATCH",
        "metals:vehicle:SLV": "WATCH",
        "metals:vehicle:URA": "HOLD",
    }


def test_required_implementation_behavior_all_true():
    auth = load(AUTH_PATH)
    behavior = auth["required_implementation_behavior"]
    assert len(behavior) == 15
    assert all(value is True for value in behavior.values())
    assert behavior["do_not_create_new_numeric_action_thresholds"] is True
    assert behavior["do_not_execute_historical_or_candidate_policy_backtest"] is True
    assert behavior["do_not_persist_final_actions_to_database_hosted_or_runtime_state"] is True


def test_required_outputs_match_design_exactly():
    design = load(DESIGN_PATH)
    auth = load(AUTH_PATH)
    expected = {
        "final_action_policy_json",
        "twelve_asset_final_action_matrix_json",
        "final_action_explanation_contract_json",
        "forward_validation_anchor_contract_json",
        "final_action_policy_summary_json",
    }
    assert set(auth["required_outputs"].keys()) == expected
    assert set(design["required_outputs_for_future_implementation"].keys()) == expected
    assert all(value is True for value in auth["required_outputs"].values())


def test_only_two_implementation_boundaries_open():
    auth = load(AUTH_PATH)
    boundary = auth["authorization_boundary"]
    assert len(boundary) == 15
    assert {key for key, value in boundary.items() if value is True} == {
        "final_action_policy_implementation_authorized",
        "forward_validation_anchor_implementation_authorized",
    }


def test_persistence_backtest_runtime_and_execution_remain_closed():
    auth = load(AUTH_PATH)
    boundary = auth["authorization_boundary"]
    for key in [
        "runtime_implementation_authorized",
        "final_action_persistence_authorized",
        "recommendation_recompute_authorized",
        "forecast_refresh_authorized",
        "model_refresh_authorized",
        "historical_backtest_authorized",
        "candidate_policy_backtest_authorized",
        "database_write_authorized",
        "hosted_write_authorized",
        "network_collection_authorized",
        "pr_authorized",
        "main_deploy_authorized",
        "allocation_or_execution_authorized",
    ]:
        assert boundary[key] is False


def test_decision_and_next_decision():
    auth = load(AUTH_PATH)
    assert auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_DECISION_ARBITRATION_IMPLEMENTATION"
    assert auth["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_METALS_FINAL_DECISION_ARBITRATION_IMPLEMENTATION"
