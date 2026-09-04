from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

JS = (
    ROOT
    / "foundation"
    / "production"
    / "dashboard_assets"
    / "recommendation_ui.js"
)

CSS = (
    ROOT
    / "foundation"
    / "production"
    / "dashboard_assets"
    / "recommendation_visual.css"
)


def js() -> str:
    return JS.read_text(encoding="utf-8-sig")


def css() -> str:
    return CSS.read_text(encoding="utf-8-sig")


def test_native_visual_helpers_exist() -> None:
    source = js()

    assert "function mtgNativeAuthorityCount(p){" in source
    assert "function mtgNativeReturnDirection(p){" in source
    assert "function mtgNativePriceJourney(p){" in source
    assert "function mtgNativeAuthorityVisual(p){" in source


def test_card_is_investment_first() -> None:
    source = js()

    start = source.index(
        "function mtgNativeCard(item){"
    )

    end = source.index(
        "function mtgNativeMissingReasons(item){",
        start,
    )

    card = source[start:end]

    assert "Expected 1Y return" in card
    assert "1Y modeled target" in card
    assert "Current" in card
    assert "mtgNativePriceJourney(p)" in card
    assert "mtg-native-rank-badge" in card
    assert "Open research &rarr;" in card


def test_card_separates_purchase_tier_and_evidence() -> None:
    source = js()

    assert "Native purchase tier" in source
    assert "Ranking evidence state" in source
    assert "Actionability" in source

    assert (
        "Source ranking-evidence field; it is not the purchase tier."
        in source
    )


def test_asset_lane_authority_is_promoted_only_when_observed() -> None:
    source = js()

    start = source.index(
        "function mtgNormalizeNativeDetailAuthority("
    )

    end = source.index(
        "async function mtgHydrateNativeResearch(",
        start,
    )

    normalizer = source[start:end]

    assert "asset.lane_authority_state" in normalizer

    assert (
        "if(mtgNativeHasValue(asset.lane_authority_state))"
        in normalizer
    )

    assert (
        "normalized.lane_authority_state="
        in normalizer
    )


def test_detail_hero_is_return_and_price_relationship_focused() -> None:
    source = js()

    start = source.index(
        "async function openMtgNativeDetail(page,item){"
    )

    end = source.index(
        "async function renderMtgDomain(",
        start,
    )

    detail = source[start:end]

    assert "GOVERNED 1-YEAR OUTLOOK" in detail
    assert "modeled 1Y return" in detail
    assert "mtgNativePriceJourney(p)" in detail

    assert "Current market" in detail
    assert "1Y modeled target" in detail
    assert "Native lane rank" in detail


def test_no_synthetic_bear_base_bull_or_sparkline_is_added() -> None:
    source = js()

    start = source.index(
        "function mtgNativeCard(item){"
    )

    end = source.index(
        "function mtgNativeMissingReasons(item){",
        start,
    )

    card = source[start:end]

    assert "Bear" not in card
    assert "Bull" not in card
    assert "svgSparkline" not in card
    assert "riskScore(" not in card


def test_missing_forecast_gets_no_fake_visual_values() -> None:
    source = js()

    assert (
        "Current-to-target visualization unavailable"
        in source
    )

    assert (
        '!forecastAvailable'
        in source
        or "!forecastAvailable" in source
    )

    assert '"Missing"' in source


def test_authority_visual_is_not_labeled_as_risk() -> None:
    source = js()

    start = source.index(
        "function mtgNativeAuthorityVisual(p){"
    )

    end = source.index(
        "function mtgNativeCard(item){",
        start,
    )

    helper = source[start:end]

    assert "Authority coverage" in helper
    assert "risk score" not in helper.lower()


def test_crypto_quality_visual_css_exists() -> None:
    stylesheet = css()

    assert "MTG_CRYPTO_QUALITY_VISUAL_PARITY_V1" in stylesheet

    assert ".mtg-native-card-thesis{" in stylesheet
    assert ".mtg-native-journey{" in stylesheet
    assert ".mtg-native-rank-badge{" in stylesheet
    assert ".mtg-native-thesis-grid{" in stylesheet

    assert "transform:translateY(-2px)" in stylesheet


def test_governance_boundaries_still_exist() -> None:
    source = js()

    assert (
        "No universal MTG rank or cross-domain rank is created."
        in source
    )

    assert (
        "Recommendation does not authorize execution."
        in source
    )

    assert (
        "Secret Lair premium fields and Q10 purchase policy"
        in source
    )

def test_native_research_button_is_bound_to_detail_renderer() -> None:
    source = js()

    assert (
        'class="rec-research-button rec-mtg-native-detail"'
        in source
    )

    assert (
        'data-asset-id="${escapeHtml(item.asset_id)}"'
        in source
    )

    assert (
        "function bindMtgNativeButtons(page,items){"
        in source
    )

    assert '".rec-mtg-native-detail"' in source
    assert "button.dataset.assetId" in source
    assert "String(item.asset_id)" in source
    assert "button.addEventListener(" in source
    assert '"click"' in source
    assert "await openMtgNativeDetail(" in source

    assert (
        "bindMtgNativeButtons(\n"
        "      page,\n"
        "      visible"
        in source
    )

def test_native_detail_observed_record_panel_exists() -> None:
    source = js()

    assert (
        "function mtgNativeObservedRecordPanel(detail){"
        in source
    )

    assert "Object.keys(records)" in source

    assert (
        "Generic UIP presentation records"
        in source
    )

    assert (
        "mtgNativeObservedRecordPanel(detail)"
        in source
    )


def test_secret_lair_research_button_is_bound_to_detail_renderer() -> None:
    source = js()

    assert (
        'class="rec-research-button rec-mtg-premium-detail"'
        in source
    )

    assert (
        "function bindMtgPremiumButtons(page,items){"
        in source
    )

    assert '".rec-mtg-premium-detail"' in source
    assert "button.dataset.assetId" in source

    assert (
        "await openMtgPremiumDetail("
        in source
    )

    assert (
        "bindMtgPremiumButtons(\n"
        "      page,\n"
        "      visible"
        in source
    )


def test_k3g7c_rich_lane_native_detail_hydration() -> None:
    source = js()

    assert source.count(
        "function mtgNativeRankNumber(item){"
    ) == 1

    for token in (
        "mtg_collector_research",
        "mtg_collector_forecast_horizon",
        "mtg_precollector_research",
        "mtg_precollector_scenario_horizon",
        "calibration_status_365",
        "calibration_status_1095",
        "weighted_score_before_penalty",
        "purchase_eligible_at_this_stage",
        "high_confidence_rank",
        "speculative_rank",
        "model_rank",
        "directly_backtested_at_this_horizon",
    ):
        assert token in source

    assert (
        "function mtgNativeCollectorResearchPanel(detail){"
        in source
    )

    assert (
        "function mtgNativePreCollectorResearchPanel(detail){"
        in source
    )

    assert (
        "function mtgNativeRichResearchPanel(item,detail){"
        in source
    )

    assert (
        "${mtgNativeRichResearchPanel(item,detail)}"
        in source
    )


def test_k3g7c_collector_detail_uses_real_horizon_evidence() -> None:
    source = js()

    start = source.index(
        "function mtgNativeCollectorResearchPanel(detail){"
    )

    end = source.index(
        "function mtgNativePreCollectorResearchPanel(detail){",
        start,
    )

    panel = source[start:end]

    assert "horizon_days" in panel
    assert "median_price" in panel
    assert "median_expected_return" in panel
    assert "probability_of_loss" in panel
    assert "probability_of_50pct_gain" in panel
    assert "probability_of_doubling" in panel

    assert (
        "UIP does not interpolate missing horizons or manufacture"
        in panel
    )

    assert (
        "Bear/Base/Bull scenarios."
        in panel
    )

    for forbidden in (
        "<th>Bear</th>",
        "<th>Base</th>",
        "<th>Bull</th>",
        ">Bear case<",
        ">Base case<",
        ">Bull case<",
    ):
        assert forbidden not in panel


def test_k3g7c_collector_ranking_stage_semantic_is_not_final_purchase_authority() -> None:
    source = js()

    assert "Ranking-stage eligibility" in source

    assert (
        "Context only; final purchase authority is separate"
        in source
    )

    assert (
        "purchase_recommendations_authorized"
        not in source
    )


def test_k3g7c_precollector_ranks_remain_separate() -> None:
    source = js()

    start = source.index(
        "function mtgNativePreCollectorResearchPanel(detail){"
    )

    end = source.index(
        "function mtgNativeRichResearchPanel(item,detail){",
        start,
    )

    panel = source[start:end]

    assert "Purchase rank" in panel
    assert "High-confidence rank" in panel
    assert "Speculative rank" in panel
    assert "Model rank" in panel

    assert (
        "Purchase rank, high-confidence rank, speculative rank, and per-horizon"
        in panel
    )


def test_k3g7c_precollector_scenarios_are_not_relabelled_as_backtested_forecasts() -> None:
    source = js()

    start = source.index(
        "function mtgNativePreCollectorResearchPanel(detail){"
    )

    end = source.index(
        "function mtgNativeRichResearchPanel(item,detail){",
        start,
    )

    panel = source[start:end]

    assert (
        "Scenario only - not directly backtested"
        in panel
    )

    assert (
        "directly_backtested_at_this_horizon"
        in panel
    )

    assert (
        "The 3Y/5Y rows are scenario"
        in panel
    )

    assert (
        "not relabeled as directly backtested forecasts"
        in panel
    )


def test_k3g7c_rich_detail_css_exists() -> None:
    stylesheet = css()

    assert "MTG_LANE_NATIVE_RICH_DETAIL_V1" in stylesheet
    assert ".mtg-native-rich-panel{" in stylesheet
    assert ".mtg-native-rich-kpis{" in stylesheet
    assert ".mtg-native-scenario-grid{" in stylesheet
    assert ".mtg-native-scenario-card{" in stylesheet


def test_k3g7fb_compact_cards_move_secondary_semantics_into_disclosure() -> None:
    source = js()

    start = source.index(
        "function mtgNativeCard(item){"
    )

    end = source.index(
        "function mtgNativeMissingReasons(item){",
        start,
    )

    card = source[start:end]

    assert '<details class="mtg-native-card-secondary">' in card
    assert "Decision context" in card

    assert "Native purchase tier" in card
    assert "Ranking evidence state" in card
    assert "Actionability" in card

    assert "Expected 1Y return" in card
    assert "1Y modeled target" in card
    assert "mtgNativeAuthorityVisual(p)" in card

    assert card.index("Open research") < card.index("Decision context")


def test_k3g7fb_collector_chart_uses_only_governed_populated_horizons() -> None:
    source = js()

    start = source.index(
        "function mtgNativeCollectorHorizonChart(horizons){"
    )

    end = source.index(
        "function mtgNativeCollectorResearchPanel(detail){",
        start,
    )

    chart = source[start:end]

    assert "horizon_days" in chart
    assert "p10_price" in chart
    assert "median_price" in chart
    assert "p90_price" in chart

    assert "rows.length<2" in chart
    assert "No missing horizon is interpolated." in chart

    assert "Bear case" not in chart
    assert "Base case" not in chart
    assert "Bull case" not in chart

    assert "mtg-native-horizon-line p10" in chart
    assert "mtg-native-horizon-line median" in chart
    assert "mtg-native-horizon-line p90" in chart


def test_k3g7fb_pre_scenario_outcomes_are_visually_primary() -> None:
    source = js()

    start = source.index(
        "function mtgNativePreCollectorResearchPanel(detail){"
    )

    end = source.index(
        "function mtgNativeRichResearchPanel(item,detail){",
        start,
    )

    panel = source[start:end]

    assert 'class="mtg-native-scenario-primary"' in panel
    assert "Terminal median" in panel
    assert "Median CAGR" in panel
    assert "Loss probability" in panel
    assert "Model rank ${escapeHtml(modelRank)}" in panel

    assert (
        "Scenario only - not directly backtested"
        in panel
    )


def test_k3g7fb_authority_and_governance_are_collapsed_secondary_detail() -> None:
    source = js()

    start = source.index(
        "async function openMtgNativeDetail(page,item){"
    )

    end = source.index(
        "async function renderMtgDomain(",
        start,
    )

    detail = source[start:end]

    assert (
        '<details class="rec-side-panel mtg-native-methodology-disclosure">'
        in detail
    )

    assert "Authority & methodology" in detail
    assert "<h5>Authority coverage</h5>" in detail
    assert "<h5>Authority gaps</h5>" in detail
    assert "<h5>Authority lineage</h5>" in detail
    assert "<h5>Governance boundary</h5>" in detail

    assert (
        '<details class="rec-side-panel mtg-native-methodology-disclosure" open'
        not in detail
    )

    assert "Lane-native research" in detail
    assert "Governed product and horizon evidence" in detail


def test_k3g7fb_final_refinement_css_contract() -> None:
    stylesheet = css()

    assert "MTG_FINAL_UX_REFINEMENT_V1" in stylesheet

    for token in (
        ".mtg-native-card-secondary{",
        ".mtg-native-horizon-viz{",
        ".mtg-native-horizon-line.median{",
        ".mtg-native-scenario-primary{",
        ".mtg-native-methodology-disclosure{",
    ):
        assert token in stylesheet
