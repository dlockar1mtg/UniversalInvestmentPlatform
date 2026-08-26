from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "commodity_decision_explanation_design.json"


def load_design() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_gold_is_eligible_only_for_separate_derived_explanation() -> None:
    design = load_design()
    assert design["gold"]["eligible_for_derived_rationale"] is True
    assert design["gold"]["eligible_for_forecast_regime_risk_context"] is True
    assert design["authority_semantics"]["derived_rationale_is_not_native_recommendation_rationale"] is True
    assert design["authority_semantics"]["forecast_regime_risk_context_is_not_typed_risk_metrics"] is True
    assert design["authority_semantics"]["forecast_regime_risk_context_must_not_populate_risk_metrics_current"] is True


def test_gold_explanation_is_bound_to_own_forecast_model_and_regime_evidence() -> None:
    design = load_design()
    findings = design["source_audit_findings"]
    assert findings["gold_current_forecast_present"] is True
    assert findings["gold_current_model_components_present"] is True
    assert findings["gold_current_regime_probabilities_present"] is True
    assert findings["gold_current_typed_risk_present"] is False
    assert findings["gold_historical_typed_risk_present"] is False
    assert design["gold"]["required_forecast_horizons_months"] == [3, 6, 12, 24]


def test_vehicle_risk_and_tactical_evidence_cannot_be_inherited_by_commodity() -> None:
    design = load_design()
    semantics = design["authority_semantics"]
    assert semantics["vehicle_risk_must_not_be_inherited_by_commodity"] is True
    assert semantics["vehicle_forecast_or_tactical_evidence_must_not_be_inherited_by_commodity"] is True
    assert design["source_audit_findings"]["gld_current_typed_risk_present"] is True
    assert design["source_audit_findings"]["ura_current_typed_risk_present"] is True


def test_gold_forecast_regime_risk_context_is_not_generic_native_risk() -> None:
    design = load_design()
    rules = design["gold"]["forecast_regime_risk_context_rules"]
    assert rules["semantic_label"] == "Forecast / regime risk context"
    assert rules["allowed_context_levels"] == ["ELEVATED", "MODERATE", "LOWER_REGIME_STRESS"]
    assert rules["must_explain_that_context_is_not_typed_asset_risk"] is True
    assert rules["must_not_map_to_LOW_MEDIUM_HIGH_native_risk_levels"] is True


def test_uranium_remains_unavailable_without_commodity_authority() -> None:
    design = load_design()
    uranium = design["uranium"]
    assert uranium["eligible_for_derived_rationale"] is False
    assert uranium["eligible_for_forecast_regime_risk_context"] is False
    assert uranium["reason"] == "NO_CURRENT_COMMODITY_FORECAST_MODEL_OR_REGIME_AUTHORITY"
    assert uranium["required_presentation_state"]["derived_rationale"] == "UNAVAILABLE"
    assert uranium["required_presentation_state"]["forecast_regime_risk_context"] == "UNAVAILABLE"
    assert uranium["required_presentation_state"]["must_not_infer_from_URA"] is True
    assert uranium["required_presentation_state"]["must_not_infer_from_URNM"] is True


def test_design_does_not_authorize_runtime_or_writes() -> None:
    design = load_design()
    assert all(value is False for value in design["boundaries"].values())
    assert design["next_decision"] == "AUTHORIZE_METALS_COMMODITY_DECISION_EXPLANATION_IMPLEMENTATION"
