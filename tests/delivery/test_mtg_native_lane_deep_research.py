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
    return JS.read_text(
        encoding="utf-8-sig"
    )


def css() -> str:
    return CSS.read_text(
        encoding="utf-8-sig"
    )


def test_native_cards_have_research_action() -> None:
    source = js()

    assert "rec-mtg-native-detail" in source
    assert "Open research &rarr;" in source
    assert "bindMtgNativeButtons" in source


def test_collector_and_precollector_bind_native_detail() -> None:
    source = js()

    assert 'mtgLane==="collector"' in source
    assert 'mtgLane==="pre_collector"' in source
    assert "bindMtgNativeButtons" in source
    assert "openMtgNativeDetail" in source


def test_native_detail_attempts_existing_generic_endpoint_first() -> None:
    source = js()

    assert "await readAssetDetail(item)" in source
    assert "/v1/presentation/assets/" in source


def test_native_detail_uses_certified_price_fields() -> None:
    source = js()

    assert "current_price_usd" in source
    assert "current_price_authority_available" in source

    assert "Current price authority" in source


def test_native_detail_uses_certified_forecast_fields() -> None:
    source = js()

    assert "forecast_authority_available" in source
    assert "forecast_1y_price_usd" in source
    assert "forecast_1y_return" in source

    assert "Native 1Y forecast" in source


def test_native_detail_uses_rank_and_purchase_semantics() -> None:
    source = js()

    assert "native_rank_type" in source
    assert "native_purchase_status" in source or "nativeStatus(item)" in source
    assert "purchase_semantic" in source


def test_missing_authority_remains_explicit() -> None:
    source = js()

    assert "mtgNativeMissingReasons" in source
    assert "No governed current-price authority is available." in source
    assert "No governed one-year forecast authority is available." in source

    assert "Missing authority remains missing" in source


def test_lineage_is_visible() -> None:
    source = js()

    assert "native_authority_pointer" in source
    assert "native_authority_sha256" in source
    assert "Authority lineage" in source


def test_secret_lair_semantics_are_not_reused() -> None:
    source = js()

    assert (
        "Secret Lair premium fields and Q10 purchase policy do not apply to this lane"
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


def test_native_deep_research_visuals_are_external() -> None:
    stylesheet = css()

    assert (
        "/* MTG_NATIVE_LANE_DEEP_RESEARCH_V1 */"
        in stylesheet
    )

    assert ".mtg-native-detail-authority-grid" in stylesheet
    assert ".mtg-native-missing-list" in stylesheet
    assert ".mtg-native-record-groups" in stylesheet
