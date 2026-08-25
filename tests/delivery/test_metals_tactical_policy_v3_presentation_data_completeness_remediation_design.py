from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/metals/tactical_policy_v3_presentation_data_completeness_remediation_design.json"
VERIFIER = ROOT / "scripts/verify_metals_tactical_policy_v3_presentation_data_completeness_remediation_design.py"


def load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_design_is_bound_to_certified_audit_and_database() -> None:
    payload = load()
    assert payload["source_audit_head"] == "dd6f5df48b5324b0bbfc3e7db7bb35b7642df11c"
    assert payload["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_existing_evidence_is_reused_semantically() -> None:
    payload = load()
    mappings = payload["approved_semantic_mappings"]
    assert mappings["vehicle_tactical_context"]["source"] == "metals_tactical_state_current"
    assert mappings["vehicle_forecast_return_context"]["source"] == "metals_uncertainty_adjusted_view_current"
    assert mappings["vehicle_recommendation_explanation"]["source"] == "metals_recommendation_change_current"
    assert mappings["commodity_model_components"]["source"] == "metals_forecast_model_component_current"
    assert mappings["commodity_regime_probabilities"]["source"] == "metals_regime_probability_current"


def test_false_semantic_substitutions_are_forbidden() -> None:
    payload = load()
    rejected = payload["explicitly_rejected_false_mappings"]
    assert rejected["price_semantics_is_current_price"] is False
    assert rejected["downside_penalty_is_forecast_lower_bound"] is False
    assert rejected["uncertainty_penalty_is_risk_score"] is False


def test_unresolved_fields_remain_unresolved() -> None:
    payload = load()
    unresolved = payload["genuinely_unresolved_fields"]
    assert "numeric_current_price" in unresolved
    assert "forecast_upper_bound" in unresolved
    assert "forecast_lower_bound" in unresolved
    assert "generic_risk_level" in unresolved
    assert "commodity_tactical_state" in unresolved


def test_design_preserves_governance_boundaries() -> None:
    payload = load()
    assert all(value is False for value in payload["boundaries"].values())
    assert payload["presentation_strategy"]["bil_remains_reference_control_only"] is True
    assert payload["presentation_strategy"]["no_cross_domain_rank"] is True
    assert payload["presentation_strategy"]["no_execution_authority"] is True


def test_verifier_is_read_only() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    forbidden = ("duckdb.connect", "INSERT ", "UPDATE ", "DELETE ", "requests.", "urllib.request")
    assert not any(token in source for token in forbidden)
