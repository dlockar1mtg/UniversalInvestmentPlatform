from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

JS = (
    ROOT
    / "foundation"
    / "production"
    / "dashboard_assets"
    / "recommendation_ui.js"
)


def source() -> str:
    return JS.read_text(
        encoding="utf-8-sig"
    )


def test_frontend_consumes_existing_certified_mtg_endpoint() -> None:
    javascript = source()

    assert "/v1/presentation/mtg-research/" in javascript
    assert "readMtgPremiumResearch" in javascript
    assert "hydrateMtgPremiumResearch" in javascript

    assert "premium_research" in javascript


def test_only_secret_lair_identity_is_premium_candidate() -> None:
    javascript = source()

    assert "isSecretLairPremiumCandidate" in javascript
    assert 'startsWith("SECRET_LAIR_V1_1|")' in javascript


def test_mtg_domain_has_premium_card_and_detail_surface() -> None:
    javascript = source()

    assert "renderMtgDomain" in javascript
    assert "mtgPremiumCard" in javascript
    assert "openMtgPremiumDetail" in javascript

    assert "SECRET LAIR PREMIUM RESEARCH" in javascript
    assert "Open investment research" in javascript


def test_q10_purchase_policy_is_visually_explicit() -> None:
    javascript = source()

    assert "Governed Q10 entry" in javascript
    assert "current_tcg_market_price_usd" in javascript
    assert "y1_q10_break_even_entry_price_usd" in javascript
    assert "current_price_vs_q10_break_even_state" in javascript

    start = javascript.index(
        "function mtgDistanceToQ10(premium){"
    )

    end = javascript.index(
        "function mtgGovernedQ10State(",
        start,
    )

    distance_function = javascript[start:end]

    assert "return q10-current;" in distance_function

    assert (
        "current_price_margin_to_q10_break_even"
        not in distance_function
    )

    assert "Q25 and Q50 are diagnostic context only" in javascript


def test_certified_one_year_outlook_is_visible() -> None:
    javascript = source()

    assert "Certified 1Y outlook" in javascript
    assert "Certified 1Y forecast" in javascript

    assert "certified_1y_point_forecast_usd" in javascript
    assert "certified_1y_point_return" in javascript

    assert "y1_probability_of_loss" in javascript
    assert "y1_probability_of_positive_return" in javascript

    assert "y1_q10_terminal_value_usd" in javascript
    assert "y1_q50_terminal_value_usd" in javascript
    assert "y1_q90_terminal_value_usd" in javascript


def test_three_and_five_year_values_remain_scenarios() -> None:
    javascript = source()

    assert "3Y scenario" in javascript
    assert "5Y scenario" in javascript

    assert "y3_median_total_return_scenario" in javascript
    assert "y5_median_total_return_scenario" in javascript

    assert "y3_probability_of_loss_scenario" in javascript
    assert "y5_probability_of_loss_scenario" in javascript

    assert (
        "scenario distributions, not direct certified forecasts"
        in javascript
    )

    assert (
        "3Y and 5Y are scenarios only"
        in javascript
    )


def test_evidence_context_is_visible() -> None:
    javascript = source()

    assert "Evidence strength" in javascript

    assert "own_history_evidence_class" in javascript
    assert "history_span_days" in javascript
    assert "historical_observation_count" in javascript

    assert "exact_structural_comparable_product_count" in javascript
    assert "global_comparable_product_count" in javascript

    assert "source_authority_path" in javascript


def test_missing_premium_authority_remains_missing() -> None:
    javascript = source()

    assert "Premium research unavailable for this lane" in javascript

    assert (
        "UIP does not synthesize Secret Lair premium authority"
        in javascript
    )

    assert "premium_research:null" in javascript


def test_native_rank_remains_mtg_only_and_nonexecuting() -> None:
    javascript = source()

    assert (
        "MTG native rank is used only inside MTG"
        in javascript
    )

    assert (
        "cannot override the governed Q10 purchase policy"
        in javascript
    )

    assert (
        "No universal MTG rank or cross-domain rank is created"
        in javascript
    )

    assert (
        "Recommendation does not authorize execution"
        in javascript
    )


def test_existing_crypto_and_metals_renderers_remain_present() -> None:
    javascript = source()

    assert "renderCryptoDomain" in javascript
    assert "renderMetalsDomain" in javascript

    assert "3-YEAR GROWTH OUTLOOK" in javascript
    assert "Long-term thesis + tactical opportunity" in javascript
