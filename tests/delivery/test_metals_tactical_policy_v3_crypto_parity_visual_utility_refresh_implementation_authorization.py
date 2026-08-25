import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config/metals/tactical_policy_v3_crypto_parity_visual_utility_refresh_implementation_authorization.json"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_authorization_identity_and_source():
    data = load()
    assert data["authorization_id"] == "METALS-TACTICAL-POLICY-V3-CRYPTO-PARITY-VISUAL-UTILITY-REFRESH-IMPLEMENTATION-AUTHORIZATION-1"
    assert data["source_design_head"] == "aaf9278aa6d973a78663836174849bf78df7a447"
    assert data["production_main_baseline_head"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"


def test_exact_runtime_file_scope():
    data = load()
    assert data["authorized_runtime_files"] == [
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/dashboard.css",
    ]


def test_visual_behavior_requirements():
    required = load()["required_behavior"]
    assert required["card_first_metals_overview"] is True
    assert required["all_metals_table_retained_as_secondary_view"] is True
    assert required["visible_rationale_and_risk"] is True
    assert required["price_history_visual_when_supported"] is True
    assert required["momentum_visual_when_supported"] is True
    assert required["drawdown_visual_when_supported"] is True
    assert required["forecast_or_scenario_visual_when_supported"] is True
    assert required["dedicated_tactical_context_panel"] is True


def test_semantic_boundaries():
    required = load()["required_behavior"]
    assert required["tactical_context_separate_from_long_term_thesis"] is True
    assert required["bil_reference_control_only"] is True
    assert required["bil_excluded_from_featured_opportunities"] is True
    assert required["no_tactical_overlay_not_sell"] is True


def test_only_runtime_implementation_is_authorized():
    boundaries = load()["implementation_boundaries"]
    assert boundaries["runtime_implementation_authorized"] is True
    for key, value in boundaries.items():
        if key != "runtime_implementation_authorized":
            assert value is False


def test_existing_domain_behavior_preserved():
    strategy = load()["implementation_strategy"]
    assert strategy["reuse_existing_recommendation_ui_architecture"] is True
    assert strategy["reuse_existing_crypto_card_and_detail_visual_language"] is True
    assert strategy["preserve_crypto_behavior"] is True
    assert strategy["preserve_mtg_behavior"] is True


def test_next_decision_is_bounded_implementation():
    assert load()["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH"
