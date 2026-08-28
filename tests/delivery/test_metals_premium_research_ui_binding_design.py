from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "premium_research_ui_binding_design.json"


def load_design() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8-sig"))


def test_design_binds_certified_active_authority() -> None:
    design = load_design()
    assert design["design_id"] == "METALS-PREMIUM-RESEARCH-UI-BINDING-DESIGN-1"
    assert design["source_governed_head"] == "40c8f19507c44d44e433dc6835a774858f81e791"
    assert design["active_publication_id"] == "metals-mtg-composite-recovery-r1-20260828"
    assert design["active_content_fingerprint"] == "67352221b51e7479fe9e154e12dd718a9cf392c794d2320461203fe980bfc009"
    assert design["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_design_preserves_decision_and_supporting_semantics() -> None:
    design = load_design()
    guards = design["semantic_guards"]
    assert guards["final_action_is_only_primary_action"] is True
    assert guards["native_recommendation_is_supporting_evidence_only"] is True
    assert guards["tactical_state_never_replaces_final_action"] is True
    assert guards["uncertainty_adjusted_return_is_supporting_evidence_only"] is True
    assert guards["commodity_vehicle_inference_prohibited"] is True
    assert guards["cross_domain_rank_prohibited"] is True
    assert guards["automatic_execution_prohibited"] is True
    assert guards["missing_values_must_not_be_synthesized"] is True
    assert design["overview_design"]["reference_control_handling"] == "BIL_MUST_RENDER_AS_REFERENCE_CONTROL_NOT_INVESTMENT_OPPORTUNITY"


def test_design_uses_only_observed_bound_evidence_and_keeps_implementation_closed() -> None:
    design = load_design()
    inventory = design["binding_inventory"]
    assert design["evidence_basis"] == "EXISTING_HOSTED_CERTIFIED_PRESENTATION_RECORDS_ONLY"
    assert inventory["gold_commodity"]["forecast_horizons_months"] == [3, 6, 12, 24]
    assert inventory["gold_commodity"]["derived_decision_explanation_available"] is True
    assert inventory["uranium_commodity"]["forecast_horizons_months"] == []
    assert inventory["uranium_commodity"]["availability_reason"] == "NO_CURRENT_COMMODITY_FORECAST_MODEL_OR_REGIME_AUTHORITY"
    assert len(inventory["vehicle_current_price_and_history_assets"]) == 10
    assert len(inventory["vehicle_tactical_assets"]) == 9
    assert len(inventory["vehicle_uncertainty_adjusted_assets"]) == 8
    assert all(value is False for value in design["implementation_scope"].values())
    assert design["design_decision"] == "AUTHORIZE_BOUNDED_METALS_PREMIUM_RESEARCH_UI_IMPLEMENTATION_DESIGN"
    assert design["next_decision"] == "CERTIFY_METALS_PREMIUM_RESEARCH_UI_BINDING_DESIGN_AND_AUTHORIZE_IMPLEMENTATION"
