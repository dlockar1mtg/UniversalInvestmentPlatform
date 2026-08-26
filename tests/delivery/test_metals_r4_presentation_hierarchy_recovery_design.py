from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "r4_presentation_hierarchy_recovery_design.json"


def load_design() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_design_identity_and_r4_binding() -> None:
    design = load_design()
    assert design["design_id"] == "METALS-r4-PRESENTATION-HIERARCHY-RECOVERY-DESIGN-1"
    assert design["source_governed_head"] == "84241cf16c452c58e35e64cbcb811057d11ec060"
    assert design["active_hosted_publication"]["publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert design["active_hosted_publication"]["content_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
    assert design["active_hosted_publication"]["record_count"] == 12477


def test_gold_primary_presentation_surfaces_are_explicit() -> None:
    design = load_design()
    assert set(design["gold_required_primary_surfaces"]) == {
        "hero_summary",
        "hero_risk_context",
        "why_this_recommendation",
        "risk_summary",
        "risk_assessment",
        "overview_card",
        "secondary_table",
    }


def test_gold_native_semantics_cannot_be_fabricated() -> None:
    design = load_design()
    guardrails = design["gold_semantic_guardrails"]
    assert guardrails["derived_rationale_must_remain_labeled_derived"] is True
    assert guardrails["forecast_regime_risk_context_must_not_be_relabelled_native_risk"] is True
    assert guardrails["native_rationale_must_not_be_mutated_or_fabricated"] is True
    assert guardrails["native_risk_summary_must_not_be_mutated_or_fabricated"] is True
    assert guardrails["risk_metrics_current_must_not_be_populated_or_implied_populated"] is True
    assert guardrails["gld_risk_must_not_be_inherited_by_gold"] is True
    assert guardrails["vehicle_tactical_metrics_must_not_be_inferred_into_gold"] is True


def test_uranium_remains_unavailable_without_vehicle_inference() -> None:
    design = load_design()
    uranium = design["uranium_required_behavior"]
    assert uranium["derived_rationale_must_remain_unavailable"] is True
    assert uranium["forecast_regime_risk_context_must_remain_unavailable"] is True
    assert uranium["ura_urnm_evidence_must_not_be_inherited"] is True
    assert uranium["overview_and_detail_must_explain_unavailability_without_fabrication"] is True


def test_candidate_runtime_scope_is_exact() -> None:
    design = load_design()
    assert sorted(design["candidate_runtime_files"]) == sorted([
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/recommendation_visual.css",
    ])


def test_design_does_not_authorize_downstream_work() -> None:
    design = load_design()
    assert all(value is False for value in design["boundaries"].values())
    assert design["design_decision"] == "APPROVE_METALS_r4_PRESENTATION_HIERARCHY_RECOVERY_DESIGN_FOR_IMPLEMENTATION_AUTHORIZATION_CONSIDERATION"
    assert design["next_decision"] == "AUTHORIZE_BOUNDED_METALS_r4_PRESENTATION_HIERARCHY_RECOVERY_IMPLEMENTATION"
