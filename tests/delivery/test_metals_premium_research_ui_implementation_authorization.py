from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "premium_research_ui_implementation_authorization.json"
DESIGN = ROOT / "config" / "metals" / "premium_research_ui_binding_design.json"


def load():
    return (
        json.loads(AUTH.read_text(encoding="utf-8")),
        json.loads(DESIGN.read_text(encoding="utf-8")),
    )


def test_authorization_binds_certified_design_and_active_authority():
    auth, design = load()
    assert auth["authorization_id"] == "METALS-PREMIUM-RESEARCH-UI-IMPLEMENTATION-AUTHORIZATION-1"
    assert auth["design_id"] == design["design_id"]
    assert auth["source_database_sha256"] == design["source_database_sha256"]
    assert auth["active_publication_id"] == design["active_publication_id"]
    assert auth["active_content_fingerprint"] == design["active_content_fingerprint"]


def test_implementation_scope_is_bounded_to_ui_and_tests():
    auth, _ = load()
    contract = auth["implementation_contract"]
    closed = auth["closed_scope"]
    assert contract["recommendation_ui_change_authorized"] is True
    assert contract["delivery_test_change_authorized"] is True
    assert contract["metals_overview_must_use_premium_cards"] is True
    assert contract["metals_detail_must_use_premium_research_layout"] is True
    assert contract["final_action_must_remain_primary"] is True
    assert contract["native_recommendation_must_remain_supporting"] is True
    assert contract["tactical_state_must_remain_supporting"] is True
    assert contract["bil_must_render_as_reference_control"] is True
    assert contract["no_synthetic_cross_domain_rank"] is True
    assert contract["no_missing_value_synthesis"] is True
    assert contract["existing_certified_presentation_records_only"] is True
    assert all(value is False for value in closed.values())


def test_domain_preservation_and_next_decision():
    auth, _ = load()
    contract = auth["implementation_contract"]
    assert contract["crypto_behavior_must_remain_unchanged"] is True
    assert contract["mtg_behavior_must_remain_unchanged"] is True
    assert contract["gold_forecast_horizons_must_remain_3_6_12_24_months"] is True
    assert contract["uranium_unavailable_authority_must_be_explicit"] is True
    assert auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_PREMIUM_RESEARCH_UI_IMPLEMENTATION"
    assert auth["next_decision"] == "MATERIALIZE_AND_CERTIFY_METALS_PREMIUM_RESEARCH_UI_IMPLEMENTATION"
