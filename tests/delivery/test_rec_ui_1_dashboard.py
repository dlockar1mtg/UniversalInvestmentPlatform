from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def sources():
    return (
        (ASSETS / "recommendation_ui.js").read_text(encoding="utf-8"),
        (ASSETS / "governed_asset_picker.js").read_text(encoding="utf-8"),
        (ROOT / "foundation" / "production" / "http_service.py").read_text(encoding="utf-8"),
    )


def test_rec_ui_1_loads_certified_summary_list_and_detail_surfaces():
    javascript, _, _ = sources()
    assert "/v1/presentation/recommendation-summary" in javascript
    assert "/v1/presentation/recommendation-list?" in javascript
    assert "/v1/presentation/recommendation-detail?" in javascript
    assert "Domain-native opportunities" in javascript
    assert "Native semantics preserved" in javascript


def test_rec_ui_1_is_domain_first_and_never_creates_universal_rank():
    javascript, _, _ = sources()
    assert "data-rec-domain" in javascript
    assert "No universal cross-domain score or rank" in javascript
    assert "Stable asset identity order" in javascript
    assert "Native scope only" in javascript
    assert "native_rank_type" in javascript
    assert "universal score" in javascript.lower()
    assert "Top UIP" not in javascript


def test_rec_ui_1_exposes_governed_filters_without_cross_domain_pooling():
    javascript, _, _ = sources()
    for marker in (
        "native_status",
        "native_rank_type",
        "has_forecast",
        "has_risk",
        "current_price_authority_available",
        "manual_execution_price_check_required",
    ):
        assert marker in javascript
    assert "domain:state.domain" in javascript
    assert "state.offset" in javascript
    assert "state.limit" in javascript
    assert "Previous" in javascript and "Next" in javascript


def test_rec_ui_1_preserves_missing_and_exact_native_payloads():
    javascript, _, _ = sources()
    assert '"Not published"' in javascript
    assert '"Unpriced"' in javascript
    assert "No certified recommendation" not in javascript
    assert "recommendation_payload" in javascript
    assert "forecast_records" in javascript
    assert "risk_records" in javascript
    assert "No normalization or universal score applied" in javascript
    assert "JSON.stringify(detail.recommendation_payload" in javascript


def test_rec_ui_1_keeps_execution_manual_and_price_authority_explicit():
    javascript, _, _ = sources()
    assert "AUTOMATIC EXECUTION OFF" in javascript
    assert "Manual execution price check" in javascript
    assert "Certified current price" in javascript
    assert 'detail.automatic_purchase_execution?"Yes":"No"' in javascript
    assert 'detail.current_price_authority_available?money' in javascript


def test_rec_ui_1_static_asset_is_loaded_and_served():
    javascript, picker, http_service = sources()
    assert "rec-ui-1-script" in picker
    assert "/dashboard/assets/recommendation_ui.js?v=rec-ui-1" in picker
    assert '@app.get("/dashboard/assets/recommendation_ui.js"' in http_service
    assert 'assets / "recommendation_ui.js"' in http_service
    assert javascript.startswith("(()=>{")


def test_rec_ui_1_detail_content_is_escaped():
    javascript, _, _ = sources()
    assert "escape(detail.asset_name" in javascript
    assert "escape(detail.asset_id)" in javascript
    assert "escape(JSON.stringify(record.payload" in javascript
    assert "escape(JSON.stringify(detail.recommendation_payload" in javascript


def test_rec_ui_1_failure_isolated_to_recommendations_page():
    javascript, _, _ = sources()
    assert "Recommendation authority is unavailable" in javascript
    assert 'page.innerHTML=' in javascript
    assert "sessionStorage.removeItem" not in javascript
