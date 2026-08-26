from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "comparable_user_facing_decision_layer_design.json"


def load_design() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_source_and_audit_counts_are_bound() -> None:
    design = load_design()
    assert design["source_semantic_audit_head"] == "c103f15a38462e8a3ecbfab24cc87634cd97278e"
    assert design["certified_semantic_audit_counts"] == {
        "asset_count": 12,
        "safe_primary_status_count": 5,
        "blocked_primary_status_count": 7,
        "raw_adjusted_sign_conflict_count": 8,
        "contradiction_count": 17,
    }


def test_safe_primary_statuses_are_exact() -> None:
    design = load_design()
    rows = design["asset_decision_design"]
    safe = {
        asset_id: row["primary_user_facing_status"]
        for asset_id, row in rows.items()
        if row["status_surface_state"] == "AUTHORIZED_FROM_CERTIFIED_SEMANTIC_AUDIT"
    }
    assert safe == {
        "metals:commodity:gold": "HOLD",
        "metals:commodity:uranium": "HOLD",
        "metals:vehicle:COPX": "HOLD",
        "metals:vehicle:CPER": "HOLD",
        "metals:vehicle:URA": "HOLD",
    }


def test_six_conflicted_buy_vehicles_are_not_primary_buy() -> None:
    design = load_design()
    rows = design["asset_decision_design"]
    expected = {
        "metals:vehicle:GLD",
        "metals:vehicle:IAU",
        "metals:vehicle:PPLT",
        "metals:vehicle:SGOL",
        "metals:vehicle:SIVR",
        "metals:vehicle:SLV",
    }
    actual = {
        asset_id
        for asset_id, row in rows.items()
        if row["primary_user_facing_status"] == "DECISION_CONFLICT"
    }
    assert actual == expected
    for asset_id in expected:
        assert rows[asset_id]["native_recommendation"] == "BUY"
        assert rows[asset_id]["governed_uip_normalized_decision"] == "BUY"
        assert rows[asset_id]["status_surface_state"] == "BLOCKED_BY_NEGATIVE_UNCERTAINTY_ADJUSTED_RETURN"


def test_bil_is_reference_control_not_opportunity() -> None:
    design = load_design()
    bil = design["asset_decision_design"]["metals:vehicle:BIL"]
    assert bil["native_recommendation"] == "RESERVE_BUY"
    assert bil["governed_uip_normalized_decision"] is None
    assert bil["primary_user_facing_status"] == "REFERENCE_CONTROL"
    assert bil["status_surface_state"] == "REFERENCE_CONTROL_NOT_OPPORTUNITY"


def test_semantic_guardrails_are_closed() -> None:
    design = load_design()
    assert all(design["presentation_rules"].values())
    assert all(design["research_terminal_rules"].values())
    assert all(design["fail_closed_rules"].values())
    assert all(value is False for value in design["boundaries"].values())


def test_candidate_runtime_scope_and_next_decision_are_bound() -> None:
    design = load_design()
    assert design["candidate_runtime_files"] == [
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/recommendation_visual.css",
    ]
    assert design["next_decision"] == "AUTHORIZE_BOUNDED_METALS_COMPARABLE_USER_FACING_DECISION_LAYER_IMPLEMENTATION"
