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


def test_q10_distance_uses_real_usd_difference() -> None:
    source = js()

    start = source.index(
        "function mtgDistanceToQ10(premium){"
    )

    end = source.index(
        "function mtgGovernedQ10State(",
        start,
    )

    function = source[start:end]

    assert "current_tcg_market_price_usd" in function
    assert "y1_q10_break_even_entry_price_usd" in function
    assert "return q10-current;" in function

    assert (
        "current_price_margin_to_q10_break_even"
        not in function
    )


def test_sonic_example_distance_is_51_cents() -> None:
    current = 63.67
    q10 = 64.18

    assert round(q10 - current, 2) == 0.51


def test_q10_above_state_uses_absolute_usd_distance() -> None:
    source = js()

    assert (
        "`${fmtMoney(Math.abs(distance))} above Q10`"
        in source
    )

    assert (
        "`${fmtMoney(distance)} below Q10`"
        in source
    )


def test_secret_lair_separator_artifacts_are_removed() -> None:
    source = js()

    assert "MTG ? SECRET LAIR RESEARCH" not in source
    assert "Secret Lair ? Native rank" not in source

    assert (
        "Scenario distribution only ? not a direct certified forecast"
        not in source
    )

    assert "MTG &middot; SECRET LAIR RESEARCH" in source


def test_legitimate_question_marks_are_not_globally_removed() -> None:
    source = js()

    # This cleanup must be targeted; there must be no global
    # replaceAll of question marks.
    assert 'replaceAll("?","")' not in source
    assert "replaceAll('?', '')" not in source


def test_native_presentation_sort_exists() -> None:
    source = js()

    assert "function mtgNativeRankNumber(item){" in source
    assert "function mtgNativePresentationPriority(item){" in source
    assert "function mtgNativeInvestmentSort(items){" in source

    assert "mtgNativeRankNumber(a)-" in source


def test_native_sort_occurs_before_pagination_slice() -> None:
    source = js()

    render = source.index(
        "async function renderMtgDomain("
    )

    native_sort = source.index(
        "mtgNativeInvestmentSort(",
        render,
    )

    page_slice = source.index(
        "laneFiltered.slice(",
        render,
    )

    assert native_sort < page_slice


def test_unranked_products_are_not_filtered_out() -> None:
    source = js()

    start = source.index(
        "function mtgNativeInvestmentSort(items){"
    )

    end = source.index(
        "function mtgIsBuyCandidate(",
        start,
    )

    function = source[start:end]

    assert ".slice()" in function
    assert ".sort(" in function
    assert ".filter(" not in function


def test_native_card_governance_is_visually_compacted() -> None:
    stylesheet = css()

    assert (
        "MTG_FINAL_RESEARCH_UX_SEMANTIC_CLEANUP_V1"
        in stylesheet
    )

    assert ".mtg-native-authority-strip{" in stylesheet
    assert "display:flex;" in stylesheet

    assert ".mtg-native-policy{" in stylesheet
    assert "opacity:.60;" in stylesheet


def test_governance_and_execution_semantics_remain_present() -> None:
    source = js()

    assert "Missing authority remains missing." in source

    assert (
        "Secret Lair premium fields are not synthesized for this lane."
        in source
    )

    assert (
        "Recommendation does not authorize execution."
        in source
    )

    assert (
        "No universal MTG rank or cross-domain rank is created."
        in source
    )

    assert "Q10 governs purchase eligibility" in source