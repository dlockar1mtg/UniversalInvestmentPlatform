from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = json.loads(
    (ROOT / "config" / "metals" / "unified_decision_terminal_redesign_design.json").read_text(
        encoding="utf-8"
    )
)


def test_design_is_bound_to_current_r4_authority() -> None:
    assert DESIGN["design_id"] == "METALS-UNIFIED-DECISION-TERMINAL-REDESIGN-DESIGN-1"
    assert DESIGN["source_governed_head"] == "293f149b163f0d9e0f9915f17048eed324b8a6cf"
    assert DESIGN["active_hosted_publication"]["publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert DESIGN["active_hosted_publication"]["record_count"] == 12477


def test_neutral_tactical_state_is_demoted_to_compact_status() -> None:
    policy = DESIGN["tactical_presentation_policy"]
    assert policy["NO_TACTICAL_OVERLAY"]["display"] == "compact_status"
    assert policy["NO_TACTICAL_OVERLAY"]["large_bar_allowed"] is False
    assert policy["TACTICAL_SUPPORTIVE"]["large_bar_allowed"] is True
    assert policy["TACTICAL_DEFENSIVE"]["large_bar_allowed"] is True


def test_vehicle_native_risk_and_gold_context_remain_semantically_distinct() -> None:
    risk = DESIGN["risk_semantic_policy"]
    assert risk["vehicle_native_risk_label"] == "Risk level"
    assert risk["gold_derived_risk_label"] == "Forecast / regime risk context"
    assert risk["derived_risk_must_not_be_presented_as_native_typed_risk"] is True


def test_gold_visual_richness_does_not_require_vehicle_inference() -> None:
    gold = DESIGN["gold_terminal_requirements"]
    assert gold["forecast_path_visual_required"] is True
    assert gold["regime_probability_visual_required"] is True
    assert gold["model_component_visual_summary_required"] is True
    assert gold["must_not_use_vehicle_price_as_commodity_price"] is True
    assert gold["must_not_inherit_GLD_IAU_SGOL_risk_or_tactical_state"] is True


def test_vehicle_terminal_preserves_market_visuals_and_explains_forecasts() -> None:
    vehicle = DESIGN["vehicle_terminal_requirements"]
    assert vehicle["retain_historical_price_chart"] is True
    assert vehicle["surface_native_typed_risk_near_top"] is True
    assert vehicle["explain_raw_vs_adjusted_return_divergence"] is True
    assert vehicle["recommendation_change_evidence_secondary_only"] is True


def test_runtime_scope_and_downstream_boundaries_are_closed() -> None:
    assert set(DESIGN["candidate_runtime_files"]) == {
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/recommendation_visual.css",
    }
    assert all(value is False for value in DESIGN["boundaries"].values())
    assert DESIGN["next_decision"] == "AUTHORIZE_BOUNDED_METALS_UNIFIED_DECISION_TERMINAL_IMPLEMENTATION"
