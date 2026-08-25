import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "tactical_policy_v3_crypto_parity_visual_utility_refresh_design.json"


def load_design():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_design_identity_and_baselines():
    doc = load_design()
    assert doc["design_id"] == "METALS-TACTICAL-POLICY-V3-CRYPTO-PARITY-VISUAL-UTILITY-REFRESH-DESIGN-1"
    assert doc["source_recovery_review_head"] == "6351738eeff72270d6490ca2db7cb47380b22ccf"
    assert doc["production_main_baseline_head"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"


def test_crypto_is_visual_reference_not_semantic_copy():
    doc = load_design()
    assert doc["visual_principles"]["crypto_is_visual_reference_not_semantic_template"] is True
    assert doc["objective"] == "ADAPT_CERTIFIED_CRYPTO_PRESENTATION_PATTERNS_TO_METALS_WITH_METALS_NATIVE_ANALYTICAL_SEMANTICS"


def test_overview_is_card_first_and_table_secondary():
    doc = load_design()
    overview = doc["metals_overview"]
    assert overview["featured_opportunity_cards_required"] is True
    assert overview["all_metals_table_retained_as_secondary_view"] is True
    assert overview["reference_control_handling"]["bil_must_not_be_presented_as_featured_opportunity"] is True


def test_detail_requires_long_term_and_tactical_separation():
    doc = load_design()
    detail = doc["metals_detail"]
    assert detail["hero_long_term_thesis_required"] is True
    assert detail["rationale_panel_required"] is True
    assert detail["risk_panel_required"] is True
    assert detail["tactical_context_panel_required"] is True


def test_semantic_guardrails_are_all_enabled():
    assert all(load_design()["semantic_guardrails"].values())


def test_only_design_is_authorized():
    boundaries = load_design()["implementation_boundaries"]
    assert boundaries["visual_design_authorized"] is True
    for key, value in boundaries.items():
        if key != "visual_design_authorized":
            assert value is False, key


def test_candidate_runtime_package_is_bounded():
    assert load_design()["candidate_runtime_files"] == [
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/dashboard.css",
    ]


def test_next_decision_is_implementation_authorization():
    doc = load_design()
    assert doc["design_decision"] == "APPROVE_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH_DESIGN_FOR_IMPLEMENTATION_CONSIDERATION"
    assert doc["next_decision"] == "AUTHORIZE_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH_IMPLEMENTATION"
