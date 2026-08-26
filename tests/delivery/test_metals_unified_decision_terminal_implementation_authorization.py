from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config/metals/unified_decision_terminal_implementation_authorization.json"


def load() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8-sig"))


def test_authorization_identity_and_source_binding() -> None:
    data = load()
    assert data["authorization_id"] == "METALS-UNIFIED-DECISION-TERMINAL-IMPLEMENTATION-AUTHORIZATION-1"
    assert data["source_design_id"] == "METALS-UNIFIED-DECISION-TERMINAL-REDESIGN-DESIGN-1"
    assert data["source_design_head"] == "f1cfb0f3d48b08751d3abc092b3b15c8c2a6bce5"


def test_active_r4_is_bound() -> None:
    pub = load()["active_hosted_publication"]
    assert pub["publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert pub["record_count"] == 12477


def test_runtime_scope_is_exact() -> None:
    files = set(load()["authorized_runtime_files"])
    assert files == {
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/recommendation_visual.css",
    }


def test_required_behavior_is_fully_enabled() -> None:
    values = load()["required_implementation_behavior"]
    assert values
    assert all(value is True for value in values.values())


def test_semantic_guardrails_are_fully_enabled() -> None:
    values = load()["semantic_guardrails"]
    assert values
    assert all(value is True for value in values.values())


def test_only_runtime_implementation_is_authorized() -> None:
    boundary = load()["authorization_boundary"]
    assert boundary["runtime_implementation_authorized"] is True
    for key, value in boundary.items():
        if key == "runtime_implementation_authorized":
            continue
        assert value is False, key


def test_tactical_display_policy_is_preserved_in_authorized_behavior() -> None:
    behavior = load()["required_implementation_behavior"]
    assert behavior["neutral_tactical_state_compact_only"] is True
    assert behavior["supportive_tactical_state_prominent_exception"] is True
    assert behavior["defensive_tactical_state_prominent_exception"] is True
    assert behavior["commodity_tactical_state_compact_not_applicable"] is True


def test_gold_and_vehicle_risk_semantics_remain_distinct() -> None:
    guardrails = load()["semantic_guardrails"]
    assert guardrails["native_vehicle_risk_not_relabelled_as_gold_context"] is True
    assert guardrails["gold_forecast_regime_context_not_relabelled_native_risk"] is True


def test_forecast_semantics_remain_distinct() -> None:
    guardrails = load()["semantic_guardrails"]
    assert guardrails["adjusted_return_not_relabelled_price_forecast"] is True
    assert guardrails["uncertainty_penalties_not_relabelled_native_risk"] is True


def test_next_decision_is_implementation_and_certification() -> None:
    data = load()
    assert data["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_UNIFIED_DECISION_TERMINAL_IMPLEMENTATION"
    assert data["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_UNIFIED_DECISION_TERMINAL"
