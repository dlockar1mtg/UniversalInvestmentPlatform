from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "native_uranium_limited_historical_evidence_assessment_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "native_uranium_limited_historical_evidence_assessment_execution_authorization.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_authorization_identity_and_parent_binding() -> None:
    design = load(DESIGN_PATH)
    auth = load(AUTH_PATH)
    assert auth["authorization_id"] == "METALS-NATIVE-URANIUM-LIMITED-HISTORICAL-EVIDENCE-ASSESSMENT-EXECUTION-AUTHORIZATION-1"
    assert auth["source_design_id"] == design["design_id"]
    assert auth["source_design_head"] == "992817f8056ff4b4f6dd480d5f40dabc7e9b2246"
    assert auth["source_derivation_id"] == design["source_derivation_id"]
    assert auth["source_database_sha256"] == design["source_database_sha256"]


def test_authorized_scope_preserves_certified_outcome_and_independence() -> None:
    scope = load(AUTH_PATH)["authorized_assessment_scope"]
    assert scope["asset_id"] == "METALS:COMMODITY:URANIUM"
    assert scope["source_authority"] == "eia"
    assert scope["native_as_of_date"] == "2024-12-31"
    assert scope["future_native_observation_date"] == "2025-12-31"
    assert abs(float(scope["realized_return"]) - 0.11020651310563934) <= 1e-15
    assert scope["reconstructed_recommendation"] == "HOLD"
    assert scope["forecast_state_count"] == 8
    assert scope["distinct_native_outcome_event_count"] == 1
    assert scope["effective_independent_outcome_n"] == 1


def test_execution_behavior_is_fail_closed_and_descriptive_only() -> None:
    behavior = load(AUTH_PATH)["required_execution_behavior"]
    assert len(behavior) == 16
    assert all(value is True for value in behavior.values())
    assert behavior["do_not_count_shared_outcome_eight_times"] is True
    assert behavior["do_not_infer_universal_metals_policy_from_n_equals_one"] is True
    assert behavior["do_not_backtest_candidate_policies"] is True
    assert behavior["do_not_select_final_action_policy"] is True
    assert behavior["identify_remaining_vehicle_level_validation_gap"] is True
    assert behavior["identify_forward_validation_as_required_for_independent_sample_growth"] is True


def test_required_outputs_match_design_exactly() -> None:
    design = load(DESIGN_PATH)
    auth = load(AUTH_PATH)
    assert sorted(auth["required_outputs"].keys()) == sorted(design["required_outputs_for_future_execution"].keys())
    assert all(value is True for value in auth["required_outputs"].values())


def test_only_assessment_and_local_evidence_write_are_open() -> None:
    boundaries = load(AUTH_PATH)["authorization_boundary"]
    assert len(boundaries) == 17
    open_boundaries = {key for key, value in boundaries.items() if value is True}
    assert open_boundaries == {
        "limited_historical_evidence_assessment_authorized",
        "local_evidence_artifact_write_authorized",
    }
    assert boundaries["hosted_read_only_access_authorized"] is False
    assert boundaries["historical_backtest_authorized"] is False
    assert boundaries["candidate_policy_backtest_authorized"] is False
    assert boundaries["final_action_policy_authorized"] is False
    assert boundaries["final_action_selection_authorized"] is False
    assert boundaries["database_write_authorized"] is False
    assert boundaries["hosted_write_authorized"] is False
    assert boundaries["runtime_change_authorized"] is False


def test_decision_and_next_decision_are_exact() -> None:
    auth = load(AUTH_PATH)
    assert auth["authorization_decision"] == "AUTHORIZE_NATIVE_URANIUM_LIMITED_HISTORICAL_EVIDENCE_ASSESSMENT"
    assert auth["next_decision"] == "EXECUTE_AND_CERTIFY_NATIVE_URANIUM_LIMITED_HISTORICAL_EVIDENCE_ASSESSMENT"
