from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "native_uranium_realized_outcome_derivation_design.json"


def load_design() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_identity_and_source_bindings() -> None:
    design = load_design()
    assert design["design_id"] == "METALS-NATIVE-URANIUM-REALIZED-OUTCOME-DERIVATION-DESIGN-1"
    assert design["source_governed_head"] == "8dc0f86c2278c41e2a8dae9430fe5271245869d6"
    assert design["source_reconstruction_id"] == "METALS-POINT-IN-TIME-HISTORICAL-RECONSTRUCTION-1"


def test_alignment_findings_are_locked() -> None:
    findings = load_design()["certified_alignment_findings"]
    assert findings["reconstructed_forecast_state_count"] == 8
    assert findings["unique_reconstructed_as_of_date_count"] == 1
    assert findings["unique_reconstructed_as_of_date"] == "2024-12-31"
    assert findings["native_uranium_authority_row_count"] == 2
    assert findings["native_uranium_observation_dates"] == ["2024-12-31", "2025-12-31"]
    assert findings["native_uranium_source"] == "eia"
    assert findings["forecast_current_value_native_authority_match_count"] == 8
    assert findings["native_as_of_anchor_future_authority_available_count"] == 8
    assert findings["cutoff_anchor_future_authority_available_count"] == 1
    assert findings["reconstructed_recommendation"] == "HOLD"
    assert findings["reconstructed_recommendation_count"] == 8


def test_outcome_semantics_are_locked() -> None:
    semantics = load_design()["outcome_semantics"]
    assert semantics["forecast_horizon_anchor"] == "RECONSTRUCTED_NATIVE_AS_OF_DATE"
    assert semantics["forecast_horizon_months"] == 12
    assert semantics["native_as_of_date"] == "2024-12-31"
    assert semantics["target_outcome_date"] == "2025-12-31"
    assert semantics["realized_return_formula"] == "future_native_value / as_of_native_value - 1"
    assert semantics["vehicle_proxy_prohibited"] is True
    assert semantics["cutoff_date_must_not_replace_forecast_as_of_date"] is True


def test_independence_accounting_is_fail_closed() -> None:
    rules = load_design()["independence_and_counting_rules"]
    assert rules["forecast_state_count"] == 8
    assert rules["distinct_native_outcome_event_count"] == 1
    assert rules["same_realized_outcome_may_be_attached_to_each_forecast_state_for_traceability"] is True
    assert rules["shared_outcome_must_not_be_counted_as_eight_independent_outcomes"] is True
    assert rules["effective_independent_outcome_n_must_equal_one"] is True
    assert rules["single_outcome_event_cannot_certify_universal_metals_policy"] is True


def test_required_derivation_rules_are_exact_and_true() -> None:
    rules = load_design()["required_derivation_rules"]
    assert len(rules) == 16
    assert all(value is True for value in rules.values())


def test_output_contract_is_exact() -> None:
    outputs = load_design()["required_outputs_for_future_execution"]
    assert set(outputs) == {
        "native_uranium_realized_outcome_event_json",
        "forecast_state_outcome_alignment_csv",
        "forecast_state_outcome_alignment_json",
        "native_outcome_lineage_json",
        "independence_accounting_json",
        "derivation_invariant_checks_json",
        "derivation_summary_json",
    }
    assert all(value is True for value in outputs.values())


def test_all_execution_boundaries_remain_closed() -> None:
    boundaries = load_design()["boundaries"]
    assert len(boundaries) == 17
    assert all(value is False for value in boundaries.values())


def test_design_decision_and_next_step() -> None:
    design = load_design()
    assert design["design_decision"] == "APPROVE_BOUNDED_NATIVE_URANIUM_REALIZED_OUTCOME_DERIVATION_DESIGN_FOR_EXECUTION_AUTHORIZATION_CONSIDERATION"
    assert design["next_decision"] == "AUTHORIZE_BOUNDED_NATIVE_URANIUM_REALIZED_OUTCOME_DERIVATION"
