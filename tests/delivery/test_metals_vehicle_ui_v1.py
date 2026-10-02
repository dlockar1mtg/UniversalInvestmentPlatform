from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VEHICLE_UI = ROOT / "foundation" / "production" / "dashboard_assets" / "metals_vehicle_ui.js"
TACTICAL_UI = ROOT / "foundation" / "production" / "dashboard_assets" / "metals_tactical_ui.js"
HTTP_SERVICE = ROOT / "foundation" / "production" / "http_service.py"


def test_vehicle_ui_consumes_only_governed_implementation_records():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert 'RECORD_TYPE="metals_vehicle_implementation"' in text
    assert 'PREFERRED_LABEL="PREFERRED_IMPLEMENTATION_CANDIDATE"' in text
    assert 'ONLY_LABEL="ONLY_REGISTERED_IMPLEMENTATION"' in text
    assert "certified_rank_within_commodity" in text
    assert "certified_implementation_score" in text
    assert "expense_ratio_pct" in text
    assert "vehicle_type" in text
    assert "source_authority" in text
    assert "ranking_component_evidence_authority_id" in text


def test_vehicle_ui_renders_certified_ranking_breakdown_and_evidence():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    for field in (
        "exposure_fidelity_score",
        "cost_efficiency_score",
        "liquidity_implementation_friction_score",
        "risk_efficiency_score",
        "average_dollar_volume_usd",
        "bid_ask_spread_bps",
        "volatility",
        "downside_volatility",
        "maximum_drawdown_magnitude",
        "value_at_risk",
    ):
        assert field in text
    assert "Why this ranks here" in text
    assert "Certified implementation evidence" in text
    assert "30-session ADV" in text
    assert "Bid/ask spread" in text
    assert "Annualized volatility" in text
    assert "Historical 95% VaR" in text
    assert "Not competitively scored" in text


def test_vehicle_ui_marks_indirect_equity_exposure():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert '"miners_etf","thematic_equity_etf"' in text
    assert "Indirect equity exposure." in text
    assert "does not represent direct physical or futures ownership" in text


def test_vehicle_ui_preserves_upstream_thesis_and_silver_suppression():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert 'assetId==="metals:commodity:silver"' in text
    assert "Defensive Silver may not display a preferred implementation label." in text
    assert "would override the upstream commodity thesis" in text
    assert "No preferred-buy implementation label is authorized." in text
    assert "Vehicle ranking is downstream of the commodity thesis." in text


def test_vehicle_ui_refuses_execution_allocation_sizing_and_cron_authority():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    for field in (
        "automatic_execution_authorized",
        "portfolio_allocation_authorized",
        "position_sizing_authorized",
        "central_publication_cron_restoration_authorized",
    ):
        assert field in text
    assert "refuses execution, allocation, sizing, or cron-restoration authority" in text


def test_vehicle_ui_renders_governed_commodity_forecast_evidence():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert 'MODEL_COMPONENT_TYPE="metals_model_component"' in text
    assert 'UNCERTAINTY_TYPE="metals_uncertainty_adjusted"' in text
    assert 'REGIME_TYPE="metals_regime_probability"' in text
    assert "UIP_NATIVE_METALS_MODEL_COMPONENT_V1" in text
    assert "UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1" in text
    assert "UIP_NATIVE_METALS_REGIME_PROBABILITY_V1" in text
    assert "uip_native_benchmark_momentum" in text
    assert "uip_native_vehicle_confirmation" in text
    assert "uip_native_data_completeness_adjustment" in text
    assert "Certified forecast evidence" in text
    assert "Benchmark momentum" in text
    assert "Vehicle confirmation" in text
    assert "Neutral anchor (toward 0)" in text
    assert "Raw expected return" in text
    assert "Uncertainty haircut" in text
    assert "Adjusted expected return" in text
    assert "Current regime support" in text


def test_commodity_forecast_evidence_is_fail_closed_and_semantically_bounded():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert "components.length!==9||uncertainty.length!==3||regimes.length!==3" in text
    assert "Metals research evidence record count mismatch." in text
    assert "Duplicate Metals model component evidence." in text
    assert "Missing Metals model component evidence." in text
    assert "Metals uncertainty-adjusted identity mismatch." in text
    assert "Metals regime identity mismatch." in text
    assert "one-sided confidence haircut, not a bear/bull interval" in text
    assert "not statistically calibrated probabilities" in text
    assert "Vehicle Risk V1 remains vehicle-only" in text
    assert "do not create a separate recommendation" in text


def test_dashboard_serves_and_loads_vehicle_ui_asset():
    tactical = TACTICAL_UI.read_text(encoding="utf-8")
    service = HTTP_SERVICE.read_text(encoding="utf-8")
    assert 'script.src="/dashboard/assets/metals_vehicle_ui.js"' in tactical
    assert '@app.get("/dashboard/assets/metals_vehicle_ui.js", include_in_schema=False)' in service
    assert 'FileResponse(assets / "metals_vehicle_ui.js", media_type="text/javascript")' in service


def test_vehicle_ui_is_read_only_and_uses_existing_asset_detail_endpoint():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert 'fetch(`/v1/presentation/assets/metals/${encodeURIComponent(assetId)}`' in text
    assert 'method:"POST"' not in text
    assert "allocation" in text.lower()
    assert "execution" in text.lower()


def test_vehicle_ui_renders_certified_commodity_technical_context_v1():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert 'TECHNICAL_CONTEXT_TYPE="metals_commodity_technical_context"' in text
    assert "UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1" in text
    assert "Official monthly benchmark context" in text
    assert "1 month return" in text
    assert "3 month return" in text
    assert "6 month return" in text
    assert "Current drawdown" in text
    assert "historical_peak_value" in text
    assert "historical_peak_date" in text
    assert "source_series_id" in text
    assert "observation_count" in text
    assert "World Bank Pink Sheet monthly benchmark" in text


def test_commodity_technical_context_is_fail_closed_and_does_not_fake_daily_moving_averages():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert "must contain exactly one record for supported commodities" in text
    assert "Metals commodity technical context identity mismatch." in text
    assert "must use World Bank source authority." in text
    assert "source frequency mismatch." in text
    assert "refuses unauthorized daily moving averages." in text
    assert "Unsupported by monthly source cadence" in text
    assert "Exact-calendar-month comparisons only." in text
    assert "No interpolation, forward fill, vehicle proxy, or cross-provider imputation is used." in text


def test_uranium_commodity_technical_context_remains_unavailable_without_proxy():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert 'assetId==="metals:commodity:uranium"' in text
    assert "Uranium is unavailable in V1." in text
    assert "certified EIA source is annual" in text
    assert "No vehicle proxy, interpolation, or cross-provider substitution is used." in text


def test_commodity_technical_context_preserves_recommendation_boundary():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert "DESCRIPTIVE_COMMODITY_TECHNICAL_CONTEXT_NOT_RECOMMENDATION_NOT_EXECUTION" in text
    assert "do not change the commodity recommendation or authorize execution" in text


def test_metals_ui_validates_against_presentation_identity_bridge_without_mutating_raw_source_id():
    text = VEHICLE_UI.read_text(encoding="utf-8")
    assert 'function presentationAssetId(row)' in text
    assert 'row?._presentation_asset_id||row?.universal_asset_id' in text
    assert 'const presentationId=presentationAssetId(row);if(presentationId&&presentationId!==assetId)' in text
    assert 'if(presentationAssetId(row)!==assetId)' in text
    assert '.replace("metals:commodity:metals:commodity:"' not in text
    assert '.replaceAll("metals:commodity:metals:commodity:"' not in text
