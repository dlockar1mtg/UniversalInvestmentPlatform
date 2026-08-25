from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "tactical_policy_v3_decision_utility_completion_implementation_authorization.json"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_identity_and_source():
    data = load()
    assert data["authorization_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-COMPLETION-IMPLEMENTATION-AUTHORIZATION-1"
    assert data["source_design_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-COMPLETION-DESIGN-1"
    assert data["source_design_head"] == "caa82377a6bd5ac997bbf4d248c4fd091baedd54"


def test_exact_file_scope():
    data = load()
    assert set(data["authorized_files"]) == {
        "foundation/presentation/metals_tactical_projection.py",
        "config/presentation/dash_read_1_metals_tactical_extension.json",
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    }


def test_market_data_semantics():
    data = load()
    behavior = data["required_behavior"]
    assert behavior["vehicle_current_price_uses_current_price_usd"] is True
    assert behavior["vehicle_price_history_uses_close_usd"] is True
    assert behavior["history_semantics_remain_unadjusted_close"] is True


def test_decision_utility_behavior():
    data = load()
    behavior = data["required_behavior"]
    assert behavior["vehicle_raw_and_adjusted_return_are_distinct"] is True
    assert behavior["commodity_expected_return_horizons_3_6_12_24_are_used_when_supported"] is True
    assert behavior["no_contradictory_no_forecast_message_when_supporting_forecast_evidence_exists"] is True
    assert behavior["commodity_tactical_state_is_not_applicable"] is True


def test_unsupported_fields_preserved():
    data = load()
    unresolved = set(data["unsupported_fields"])
    assert "forecast_lower_bound" in unresolved
    assert "forecast_upper_bound" in unresolved
    assert "full_investment_rationale" in unresolved
    assert "commodity_numeric_current_price" in unresolved


def test_semantic_guardrails():
    data = load()
    assert all(data["semantic_guardrails"].values())


def test_downstream_boundaries_closed():
    data = load()
    assert not any(data["boundaries"].values())


def test_next_decision():
    data = load()
    assert data["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_DECISION_UTILITY_COMPLETION"
