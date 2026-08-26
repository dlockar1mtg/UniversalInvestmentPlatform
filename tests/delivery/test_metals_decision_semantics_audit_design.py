from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "decision_semantics_audit_design.json"


def load_design() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_design_identity_and_source_head() -> None:
    design = load_design()
    assert design["design_id"] == "METALS-DECISION-SEMANTICS-AUDIT-DESIGN-1"
    assert design["source_governed_head"] == "6fdc0a38fda452d291b74da62d96b41703d99f52"
    assert design["current_visual_acceptance"] == "REJECTED"


def test_required_asset_scope_is_exact() -> None:
    design = load_design()
    assert set(design["required_asset_scope"]) == {
        "metals:commodity:gold",
        "metals:commodity:uranium",
        "metals:vehicle:BIL",
        "metals:vehicle:COPX",
        "metals:vehicle:CPER",
        "metals:vehicle:GLD",
        "metals:vehicle:IAU",
        "metals:vehicle:PPLT",
        "metals:vehicle:SGOL",
        "metals:vehicle:SIVR",
        "metals:vehicle:SLV",
        "metals:vehicle:URA",
    }


def test_existing_normalization_is_bound() -> None:
    design = load_design()
    mapping = design["governed_existing_normalization"]["ranked_opportunity_mapping"]
    assert mapping["score_gte_75_and_positive_expected_return"] == "STRONG_BUY"
    assert mapping["score_gte_60_and_positive_expected_return"] == "BUY"
    assert mapping["score_gte_50"] == "WATCH"
    assert mapping["otherwise"] == "HOLD"
    assert design["governed_existing_normalization"]["bullish_native_action_nonpositive_or_missing_forecast_cap"] == "WATCH"


def test_audit_and_fail_closed_requirements_are_enabled() -> None:
    design = load_design()
    assert all(design["audit_questions"].values())
    assert all(design["fail_closed_rules"].values())
    assert all(design["required_outputs"].values())


def test_all_downstream_boundaries_are_closed() -> None:
    design = load_design()
    assert all(value is False for value in design["boundaries"].values())


def test_design_decisions_are_bound() -> None:
    design = load_design()
    assert design["design_decision"] == "APPROVE_METALS_DECISION_SEMANTICS_AUDIT_DESIGN_FOR_READ_ONLY_EXECUTION_AUTHORIZATION_CONSIDERATION"
    assert design["next_decision"] == "AUTHORIZE_READ_ONLY_METALS_DECISION_SEMANTICS_AUDIT"
