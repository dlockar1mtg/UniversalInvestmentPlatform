from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_metals_visual_refresh_is_card_first_and_keeps_secondary_table():
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert "function renderMetalsDomain" in source
    assert "metals-card-grid" in source
    assert "featured=filtered.filter(item=>!isBil(item))" in source
    assert "All Metals research · secondary evidence table" in source
    assert "BIL is reference/control only" in source


def test_metals_cards_surface_native_long_term_and_tactical_context():
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert "Domain score" in source
    assert "Confidence" in source
    assert "Forecast return" in source
    assert "1M momentum" in source
    assert "3M momentum" in source
    assert "6M momentum" in source
    assert "Current drawdown" in source
    assert "Defensive" in source
    assert "Neutral" in source
    assert "Supportive" in source


def test_metals_detail_reuses_crypto_quality_hierarchy_with_metals_semantics():
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert "LONG-TERM METALS OUTLOOK" in source
    assert "strategic thesis remains the primary authority" in source
    assert "Momentum & trend context" in source
    assert "Forecast & model evidence" in source
    assert "Why this recommendation" in source
    assert "Risk assessment" in source
    assert "vs MA50" in source
    assert "vs MA200" in source
    assert "Risk remains independent of tactical state and forecast return" in source


def test_metals_tactical_panel_is_enriched_but_never_replaces_long_term_thesis():
    source = read("foundation/production/dashboard_assets/metals_tactical_ui.js")
    assert 'const RECORD_TYPE="tactical_state"' in source
    assert "metals-tactical-metrics" in source
    assert "return_1m_pct" in source
    assert "return_3m_pct" in source
    assert "return_6m_pct" in source
    assert "distance_ma50_pct" in source
    assert "distance_ma200_pct" in source
    assert "current_drawdown_pct" in source
    assert "realized_volatility_3m_pct" in source
    assert "not a negative long-term thesis" in source
    assert "sell signal" in source
    assert "allocation instruction" in source


def test_visual_refresh_preserves_crypto_and_mtg_contracts():
    source = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'REC_DOMAINS=["crypto","metals","mtg"]' in source
    assert "3-YEAR GROWTH OUTLOOK" in source
    assert "forecastBy(detail,36,\"LONG_RANGE_SCENARIO_MODEL\")" in source
    assert "native_purchase_status" in source
    assert "native_rank" in source
    assert "native_rank_type" in source
    assert "manual_execution_price_check_required" in source
    assert "execution_ready_purchase_certified" in source
    assert "automatic_purchase_execution" in source


def test_visual_refresh_implementation_record_keeps_deployment_closed():
    import json

    payload = json.loads(
        read("config/metals/tactical_policy_v3_crypto_parity_visual_utility_refresh_implementation.json")
    )
    assert payload["implementation_id"] == "METALS-TACTICAL-POLICY-V3-CRYPTO-PARITY-VISUAL-UTILITY-REFRESH-IMPLEMENTATION-1"
    assert payload["runtime_files_changed"] == [
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    ]
    assert payload["authorized_runtime_file_not_changed"] == "foundation/production/dashboard_assets/dashboard.css"
    assert payload["implementation"]["card_first_metals_overview"] is True
    assert payload["implementation"]["featured_metals_cards_exclude_bil"] is True
    assert payload["implementation"]["long_term_and_tactical_layers_separate"] is True
    assert payload["implementation"]["crypto_behavior_intentionally_changed"] is False
    assert payload["implementation"]["mtg_behavior_intentionally_changed"] is False
    assert all(value is False for value in payload["boundaries"].values())
    assert payload["next_decision"] == "CERTIFY_AND_PREVIEW_METALS_V3_CRYPTO_PARITY_VISUAL_UTILITY_REFRESH"
