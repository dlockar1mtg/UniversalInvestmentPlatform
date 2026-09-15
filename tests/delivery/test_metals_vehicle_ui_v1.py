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
    assert 'detail?.records?.[RECORD_TYPE]' in text
    assert "certified_rank_within_commodity" in text
    assert "certified_implementation_score" in text
    assert "expense_ratio_pct" in text
    assert "vehicle_type" in text
    assert "source_authority" in text


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
