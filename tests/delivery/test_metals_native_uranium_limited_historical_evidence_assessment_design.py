from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "native_uranium_limited_historical_evidence_assessment_design.json"


def load_design() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_design_identity_and_source_bindings() -> None:
    payload = load_design()
    assert payload["design_id"] == "METALS-NATIVE-URANIUM-LIMITED-HISTORICAL-EVIDENCE-ASSESSMENT-DESIGN-1"
    assert payload["source_governed_head"] == "195e259816feaf151e52c791d8e5cd773e61b2f1"
    assert payload["source_derivation_id"] == "METALS-NATIVE-URANIUM-REALIZED-OUTCOME-DERIVATION-1"


def test_certified_outcome_findings_are_exact() -> None:
    findings = load_design()["certified_outcome_findings"]
    assert findings["asset_id"] == "METALS:COMMODITY:URANIUM"
    assert findings["source_authority"] == "eia"
    assert findings["native_as_of_date"] == "2024-12-31"
    assert findings["native_as_of_value"] == 50.36
    assert findings["future_native_observation_date"] == "2025-12-31"
    assert findings["future_native_value"] == 55.91
    assert abs(findings["realized_return"] - 0.11020651310563934) < 1e-15
    assert findings["forecast_state_count"] == 8
    assert findings["reconstructed_recommendation"] == "HOLD"
    assert findings["distinct_native_outcome_event_count"] == 1
    assert findings["effective_independent_outcome_n"] == 1


def test_assessment_rules_are_exact_and_true() -> None:
    rules = load_design()["required_assessment_rules"]
    assert len(rules) == 16
    assert all(value is True for value in rules.values())
    assert rules["do_not_count_shared_outcome_eight_times"] is True
    assert rules["do_not_infer_universal_metals_policy_from_n_equals_one"] is True
    assert rules["identify_remaining_vehicle_level_validation_gap"] is True


def test_required_outputs_are_exact() -> None:
    outputs = load_design()["required_outputs_for_future_execution"]
    assert set(outputs) == {
        "limited_evidence_assessment_json",
        "forecast_state_sensitivity_summary_json",
        "independence_limitations_json",
        "remaining_validation_gap_register_json",
        "assessment_summary_json",
    }
    assert all(value is True for value in outputs.values())


def test_all_boundaries_are_closed() -> None:
    boundaries = load_design()["boundaries"]
    assert len(boundaries) == 17
    assert all(value is False for value in boundaries.values())


def test_decision_and_next_decision_are_exact() -> None:
    payload = load_design()
    assert payload["design_decision"] == "APPROVE_NATIVE_URANIUM_LIMITED_HISTORICAL_EVIDENCE_ASSESSMENT_DESIGN_FOR_EXECUTION_AUTHORIZATION_CONSIDERATION"
    assert payload["next_decision"] == "AUTHORIZE_NATIVE_URANIUM_LIMITED_HISTORICAL_EVIDENCE_ASSESSMENT"
