from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

JS_PATH = (
    ROOT
    / "foundation"
    / "production"
    / "dashboard_assets"
    / "recommendation_ui.js"
)

CSS_PATH = (
    ROOT
    / "foundation"
    / "production"
    / "dashboard_assets"
    / "recommendation_visual.css"
)


def js() -> str:
    return JS_PATH.read_text(
        encoding="utf-8-sig"
    )


def css() -> str:
    return CSS_PATH.read_text(
        encoding="utf-8-sig"
    )


def test_mtg_has_three_explicit_lanes() -> None:
    source = js()

    assert 'data-mtg-lane="secret_lair"' in source
    assert 'data-mtg-lane="collector"' in source
    assert 'data-mtg-lane="pre_collector"' in source

    assert "Secret Lair" in source
    assert "Collector Boosters" in source
    assert "Pre-Collector" in source


def test_secret_lair_is_partitioned_from_other_lanes() -> None:
    source = js()

    assert "mtgLaneForItem" in source

    assert 'startsWith("SECRET_LAIR_V1_1|")' in source
    assert 'startsWith("COLLECTOR_V1|")' in source
    assert 'startsWith("PRE_COLLECTOR_V1|")' in source

    assert (
        "item=>mtgLaneForItem(item)===mtgLane"
        in source
    )


def test_secret_lair_buy_and_wait_are_prioritized() -> None:
    source = js()

    assert "mtgStatusPriority" in source
    assert "mtgInvestmentSort" in source

    assert "BUY candidates" in source
    assert "WAIT for Q10" in source


def test_secret_lair_cards_are_investment_first() -> None:
    source = js()

    assert "Current price" in source
    assert "Governed Q10 entry" in source
    assert "Certified 1Y" in source
    assert "1Y loss risk" in source
    assert "Evidence" in source

    assert "3Y scenario" in source
    assert "5Y scenario" in source

    assert "Open research →" in source


def test_q10_has_real_price_comparison_visualization() -> None:
    source = js()
    stylesheet = css()

    assert "mtgDistanceToQ10" in source
    assert "mtgEntryPercent" in source

    assert "mtg-entry-scale" in source
    assert ".mtg-entry-scale" in stylesheet

    assert "Q10 governs purchase eligibility" in source


def test_detail_reuses_crypto_quality_visual_language() -> None:
    source = js()

    assert "rec-strategic-hero" in source
    assert "rec-kpi-row" in source
    assert "rec-forecast-panel" in source
    assert "rec-detail-grid" in source

    assert "Certified 1Y distribution" in source
    assert "Evidence strength" in source


def test_three_and_five_year_outputs_remain_scenarios() -> None:
    source = js()

    assert "3Y scenario" in source
    assert "5Y scenario" in source

    assert (
        "Scenario distribution only"
        in source
    )

    assert (
        "scenario distributions, not direct certified forecasts"
        in source
    )


def test_collector_and_precollector_do_not_show_repetitive_premium_gap_cards() -> None:
    source = js()

    assert "mtgNativeCard" in source

    assert (
        "Collector authority remains native"
        in source
    )

    assert (
        "Pre-Collector authority remains native"
        in source
    )

    assert (
        "Secret Lair premium fields are not synthesized for this lane"
        in source
    )


def test_mtg_styles_live_in_external_stylesheet() -> None:
    source = js()
    stylesheet = css()

    assert "mtg-premium-visual-styles" not in source

    assert (
        "/* MTG_CRYPTO_PARITY_REDESIGN_V1 */"
        in stylesheet
    )

    assert ".mtg-lane-tabs" in stylesheet
    assert ".mtg-investment-card" in stylesheet
    assert ".mtg-detail-strategic-hero" in stylesheet


def test_governance_stays_locked_but_secondary() -> None:
    source = js()

    assert (
        "Q25 and Q50 are diagnostic context only"
        in source
    )

    assert (
        "MTG native rank is used only inside MTG"
        in source
    )

    assert (
        "No universal MTG rank or cross-domain rank is created"
        in source
    )

    assert (
        "Recommendation does not authorize execution"
        in source
    )
