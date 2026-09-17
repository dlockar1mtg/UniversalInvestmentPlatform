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
    assert "Data completeness adjustment" in text
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
