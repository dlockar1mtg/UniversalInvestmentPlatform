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


def test_native_detail_normalizer_exists() -> None:
    source = js()

    assert "function mtgNormalizeNativeDetailAuthority(" in source
    assert "function mtgNativeRecordPayload(" in source
    assert "function mtgNativePayload(" in source


def test_visible_native_page_hydration_exists() -> None:
    source = js()

    assert "async function mtgHydrateNativeResearch(" in source
    assert "await mtgHydrateNativeResearch(" in source

    assert 'mtgLane==="collector"' in source
    assert 'mtgLane==="pre_collector"' in source


def test_asset_record_promotes_current_price() -> None:
    source = js()

    assert "asset.current_price_authority_available" in source
    assert "asset.current_price_usd" in source

    assert (
        "normalized.current_price_usd="
        in source
    )


def test_forecast_record_promotes_target_and_return() -> None:
    source = js()

    assert "forecast.forecast_authority_available" in source
    assert "forecast.point_forecast" in source
    assert "forecast.expected_return" in source

    assert "normalized.forecast_1y_price_usd=" in source
    assert "normalized.forecast_1y_return=" in source


def test_forecast_metadata_is_promoted() -> None:
    source = js()

    assert "forecast.forecast_horizon_months" in source
    assert "forecast.forecast_method" in source

    assert "normalized.forecast_horizon_months=" in source
    assert "normalized.forecast_method=" in source


def test_catalog_missing_cannot_override_observed_detail() -> None:
    source = js()

    asset_index = source.index(
        "const observedPriceAuthority="
    )

    price_index = source.index(
        "normalized.current_price_usd=",
        asset_index
    )

    assert price_index > asset_index

    forecast_index = source.index(
        "const observedForecastAuthority="
    )

    target_index = source.index(
        "normalized.forecast_1y_price_usd=",
        forecast_index
    )

    assert target_index > forecast_index


def test_true_missing_semantics_are_preserved() -> None:
    source = js()

    assert "Missing authority remains missing." in source

    assert (
        "Secret Lair premium fields are not synthesized for this lane."
        in source
    )

    assert (
        "Secret Lair premium fields and Q10 purchase policy do not apply to this lane."
        in source
    )


def test_crypto_quality_primary_metrics_are_present() -> None:
    source = js()

    assert "Current market" in source
    assert "1Y modeled target" in source
    assert "Expected 1Y return" in source

    stylesheet = css()

    assert ".mtg-native-primary-metrics" in stylesheet
    assert ".mtg-native-primary-return" in stylesheet


def test_raw_records_are_secondary_provenance() -> None:
    source = js()

    assert "Technical provenance" in source
    assert "Generic UIP presentation records" in source

    stylesheet = css()

    assert ".mtg-native-provenance-panel" in stylesheet
    assert ".mtg-native-provenance-summary" in stylesheet


def test_semantic_boundaries_are_preserved() -> None:
    source = js()

    assert (
        "No universal MTG rank or cross-domain rank is created."
        in source
    )

    assert (
        "Recommendation does not authorize execution."
        in source
    )

    assert "mtgGovernedQ10State" in source
    assert "scenario distributions" in source
