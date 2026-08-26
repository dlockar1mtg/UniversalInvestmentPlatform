from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_csp_visual_acceptance_recovery_authorization.json"


def load() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_visual_recovery_authorization_is_bound_to_failed_preview_and_r3() -> None:
    document = load()
    assert document["source_visual_acceptance_result"] == "FAIL"
    assert document["source_governed_head"] == "2cc7fc1a0fd4f1394daf81d1631b010560e0927b"
    assert document["source_active_publication_id"] == "metals-v3-decision-utility-r3-20260826"
    assert document["source_active_publication_fingerprint"] == "e5f0bce3eb0181983e990e3de5795867dc53bf41c0d038b0d7302e722434b3ee"
    assert document["source_active_publication_record_count"] == 12475


def test_visual_recovery_authorizes_exactly_three_presentation_files() -> None:
    document = load()
    assert document["authorized_runtime_files"] == [
        "foundation/production/dashboard_assets/recommendation_visual.css",
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    ]


def test_visual_recovery_requires_csp_compatible_external_styles() -> None:
    document = load()
    required = document["required_recovery_behavior"]
    assert required["move_metals_visual_rules_to_external_recommendation_stylesheet"] is True
    assert required["remove_dynamic_metals_style_element_injection"] is True
    assert required["replace_metals_specific_inline_style_attributes_with_css_classes"] is True
    assert required["restore_three_column_desktop_metals_card_grid"] is True
    assert required["restore_structured_metals_research_hero_and_two_column_detail_layout"] is True
    assert required["restore_vehicle_history_chart_presentation"] is True


def test_visual_recovery_preserves_data_and_semantics() -> None:
    document = load()
    assert all(document["data_and_semantic_invariants"].values())


def test_visual_recovery_keeps_downstream_boundaries_closed() -> None:
    document = load()
    boundary = document["authorization_boundary"]
    assert boundary["csp_visual_recovery_authorized"] is True
    for key, value in boundary.items():
        if key == "csp_visual_recovery_authorized":
            continue
        assert value is False


def test_visual_recovery_decision_and_next_step() -> None:
    document = load()
    assert document["authorization_decision"] == "AUTHORIZE_BOUNDED_CSP_COMPATIBLE_METALS_VISUAL_ACCEPTANCE_RECOVERY"
    assert document["next_decision"] == "IMPLEMENT_AND_CERTIFY_CSP_COMPATIBLE_METALS_VISUAL_ACCEPTANCE_RECOVERY"
