from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_recommendation_catalog_joins_governed_identity_without_mutating_native_payload():
    source = read("foundation/presentation/read_api.py")
    assert "def recommendation_catalog" in source
    assert "record_type='recommendation'" in source
    assert "ar.record_type='asset'" in source
    assert 'identity.get("asset_name")' in source
    assert 'identity.get("product_name")' in source
    assert '"payload": dict(payload)' in source
    assert '@app.get("/v1/presentation/recommendation-catalog")' in source


def test_rec_ui_uses_native_domain_contracts_and_never_creates_universal_rank():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'REC_DOMAINS=["crypto","metals","mtg"]' in javascript
    assert "/v1/presentation/recommendation-catalog" in javascript
    assert "native_recommendation" in javascript
    assert "native_purchase_status" in javascript
    assert "native_rank" in javascript
    assert "native_rank_type" in javascript
    assert "evidence_state" in javascript
    assert "actionability_state" in javascript
    assert "manual_execution_price_check_required" in javascript
    assert "execution_ready_purchase_certified" in javascript
    assert "automatic_purchase_execution" in javascript
    assert "without manufacturing a universal score, cross-domain ranking, or automatic purchase decision" in javascript


def test_rec_ui_all_view_groups_domains_by_decision_utility():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert "renderDomainSummary" in javascript
    assert "REC_DOMAINS.map(domain=>renderDomainSummary" in javascript
    assert 'selectedDomain="all"' in javascript
    assert "3-year growth outlook" in javascript
    assert "Long-term thesis + tactical opportunity" in javascript
    assert "Native sealed-product opportunity" in javascript
    assert "Investment research" in javascript
    assert "Domain-native research, long-term thesis first" in javascript


def test_rec_ui_crypto_reads_asset_detail_and_uses_certified_36_month_authority():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert "/v1/presentation/assets/" in javascript
    assert "readAssetDetail" in javascript
    assert "hydrateCryptoResearch" in javascript
    assert 'forecastBy(detail,36,"LONG_RANGE_SCENARIO_MODEL")' in javascript
    assert "3Y expected return" in javascript
    assert "Bear" in javascript
    assert "Base" in javascript
    assert "Bull" in javascript
    assert "3-YEAR GROWTH OUTLOOK" in javascript
    assert "UIP does not extrapolate a shorter forecast into three years" in javascript


def test_rec_ui_crypto_detail_exposes_forecast_path_risk_and_raw_confidence():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert "forecastRows(detail)" in javascript
    assert "riskMetrics(detail)" in javascript
    assert "Forecast path & entry context" in javascript
    assert "Short horizons inform accumulation timing" in javascript
    assert "Confidence raw" in javascript
    assert "Confidence values are shown as raw source values, not percentages" in javascript
    assert "Missing probability-positive values remain missing" in javascript


def test_rec_ui_preserves_mtg_native_rank_and_execution_semantics():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'if(selectedDomain==="mtg")' in javascript
    assert "MTG native rank is used only inside MTG where provided" in javascript
    assert "manual_execution_price_check_required" in javascript
    assert "execution_ready_purchase_certified" in javascript
    assert "automatic_purchase_execution" in javascript
    assert "Recommendation does not authorize execution" in javascript


def test_rec_ui_has_search_native_status_filter_and_bounded_pagination():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'id="rec-search"' in javascript
    assert 'id="rec-status"' in javascript
    assert "REC_PAGE_SIZE=50" in javascript
    assert "offset>5000" in javascript
    assert 'id="rec-prev"' in javascript
    assert 'id="rec-next"' in javascript


def test_rec_ui_is_lazy_and_does_not_break_login_when_unauthenticated():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert 'sessionStorage.getItem("uiip-dashboard-key")' in javascript
    assert "Connect to UIP to load certified recommendations" in javascript
    assert '.nav-item[data-page="recommendations"]' in javascript
    assert "loadCatalog(false)" in javascript


def test_rec_ui_premium_visual_shell_uses_cards_scenario_ranges_and_charts():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    stylesheet = read("foundation/production/dashboard_assets/recommendation_visual.css")
    assert "rec-domain-grid" in javascript
    assert "rec-asset-grid" in javascript
    assert "rec-range" in javascript
    assert "rec-strategic-hero" in javascript
    assert "rec-range-chart" in javascript
    assert "rec-line-chart" in javascript
    assert "forecastChart(detail)" in javascript
    assert "horizonTabs(detail)" in javascript
    assert "rec-risk-gauge" in javascript
    assert ".rec-asset-card" in stylesheet
    assert ".rec-strategic-hero" in stylesheet
    assert ".rec-line-chart" in stylesheet
    assert ".rec-risk-gauge" in stylesheet


def test_dashboard_serves_and_loads_rec_ui_assets_after_core_dashboard_styles_and_script():
    service = read("foundation/production/http_service.py")
    html = read("foundation/production/dashboard_assets/dashboard.html")
    assert '@app.get("/dashboard/assets/recommendation_ui.js"' in service
    assert '@app.get("/dashboard/assets/recommendation_visual.css"' in service
    base_css = html.index('/dashboard/assets/dashboard.css')
    rec_css = html.index('/dashboard/assets/recommendation_visual.css')
    core = html.index('/dashboard/assets/dashboard.js')
    rec = html.index('/dashboard/assets/recommendation_ui.js')
    picker = html.index('/dashboard/assets/governed_asset_picker.js')
    assert base_css < rec_css
    assert core < rec < picker
    assert "REC-UI-1" in html
    assert "universal score or cross-domain rank" in html

def test_rec_ui_metals_final_action_is_primary_while_native_domain_semantics_remain():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")
    assert "function displayStatus(item)" in javascript
    assert (
        'item.domain_id==="metals"?(payload.final_action??payload.recommendation??payload.native_recommendation??null):nativeStatus(item)'
        in javascript
    )
    assert 'const status=cleanStatus(displayStatus(item))' in javascript
    assert "function nativeStatus(item)" in javascript
    assert (
        'item.domain_id==="mtg"?(payload.native_purchase_status??null):(payload.native_recommendation??payload.recommendation??null)'
        in javascript
    )
    assert 'const native=cleanStatus(nativeStatus(item));' in javascript
    assert '<td>${escapeHtml(cleanStatus(nativeStatus(item)))}</td>' in javascript
    assert '<div><span>Native recommendation</span><p>${escapeHtml(cleanStatus(nativeStatus(item)))}</p></div>' in javascript
    assert javascript.count("displayStatus(") >= 3

def test_rec_ui_metals_premium_research_implementation_contract():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")

    assert "function metalsCard(item)" in javascript
    assert "function metalsRows(items)" in javascript
    assert "function metalsForecasts(detail)" in javascript
    assert "function metalsForecastRows(detail)" in javascript

    assert "[3,6,12,24].includes(Number(row.forecast_horizon_months))" in javascript
    assert 'Number(row.forecast_horizon_months)===24' in javascript
    assert "Forecast authority unavailable for this asset. No missing forecast is synthesized." in javascript

    assert "The governed final decision is primary. Native recommendation, forecast, and risk remain supporting evidence." in javascript
    assert "<th>Final decision</th><th>Native recommendation</th>" in javascript
    assert 'cleanStatus(nativeStatus(item))' in javascript
    assert (
        'function statusFilterAllLabel(domain){'
        'return domain==="metals"?"All decision statuses":"All native statuses"}'
        in javascript
    )
    assert "statusFilterAllLabel(selectedDomain)" in javascript

    assert "BIL is reference/control only." in javascript
    assert "Featured cards exclude BIL." in javascript

    assert 'typeof renderTactical==="function"?renderTactical(detail)' in javascript
    assert "The governed long-term final decision remains authoritative." in javascript

    assert 'async function openDomain(domain)' in javascript
    assert 'if(domain==="metals")' in javascript
    assert "await hydrateMetalsResearch()" in javascript

    assert "No missing forecast is synthesized." in javascript
    assert "UIP does not manufacture a rank" in javascript


def test_rec_ui_metals_does_not_regress_crypto_or_mtg_contracts():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")

    assert 'forecastBy(detail,36,"LONG_RANGE_SCENARIO_MODEL")' in javascript
    assert "3-YEAR GROWTH OUTLOOK" in javascript
    assert "UIP does not extrapolate a shorter forecast into three years" in javascript

    assert 'if(selectedDomain==="mtg")' in javascript
    assert "MTG native rank is used only inside MTG where provided" in javascript
    assert "automatic_purchase_execution" in javascript

def test_rec_ui_metals_final_action_labels_distinguish_governed_and_native_semantics():
    javascript = read(
        "foundation/production/dashboard_assets/recommendation_ui.js"
    )

    assert (
        'function displayStatus(item){const payload=item.payload||{};'
        'return item.domain_id==="metals"?'
        '(payload.final_action??payload.recommendation??'
        'payload.native_recommendation??null):nativeStatus(item)}'
        in javascript
    )

    assert (
        'function statusFilterLabel(domain){'
        'return domain==="metals"?"Decision status":"Native status"}'
        in javascript
    )

    assert (
        'function statusFilterAllLabel(domain){'
        'return domain==="metals"?"All decision statuses":"All native statuses"}'
        in javascript
    )

    assert (
        'function recommendationColumnLabel(domain){'
        'return domain==="metals"?"Final decision":"Native recommendation"}'
        in javascript
    )

    assert "statusFilterLabel(selectedDomain)" in javascript
    assert "statusFilterAllLabel(selectedDomain)" in javascript

    assert (
        javascript.count(
            'aria-label="${escapeHtml(statusFilterLabel(selectedDomain))}"'
        )
        == 3
    )

    assert (
        javascript.count(
            '<select id="rec-status">${statusOptions}</select>'
        )
        == 0
    )

    assert "Final decision" in javascript
    assert "Native recommendation" in javascript

    assert (
        'item.domain_id==="mtg"?'
        '(payload.native_purchase_status??null):'
        '(payload.native_recommendation??payload.recommendation??null)'
        in javascript
    )


def test_rec_ui_metals_detail_identifies_final_decision_as_primary_authority():
    javascript = read(
        "foundation/production/dashboard_assets/recommendation_ui.js"
    )

    old_copy = (
        "The native recommendation, forecast, and risk evidence remain "
        "the strategic authority."
    )

    corrected_copy = (
        "The governed final decision is primary. "
        "Native recommendation, forecast, and risk remain supporting evidence."
    )

    assert old_copy not in javascript
    assert corrected_copy in javascript

    assert "Final decision" in javascript
    assert "Native recommendation" in javascript

    assert (
        'item.domain_id==="metals"?'
        '(payload.final_action??payload.recommendation??'
        'payload.native_recommendation??null):nativeStatus(item)'
        in javascript
    )


def test_dashboard_domain_health_tolerates_premium_recommendations_dom_ownership():
    dashboard = read(
        "foundation/production/dashboard_assets/dashboard.js"
    )

    recommendations = read(
        "foundation/production/dashboard_assets/recommendation_ui.js"
    )

    direct_write = (
        '$("recommendation-domain-summary").innerHTML='
    )

    guarded_write = (
        'const recommendationSummary=$("recommendation-domain-summary");'
        'if(recommendationSummary)'
        'recommendationSummary.innerHTML='
    )

    assert direct_write not in dashboard
    assert guarded_write in dashboard

    assert '$("domain-cards").innerHTML=html' in dashboard
    assert '$("refresh-domain-cards").innerHTML=items.map' in dashboard
    assert "function renderRefreshStatus(document)" in dashboard

    assert 'const page=node("recommendations")' in recommendations
    assert 'page.innerHTML=' in recommendations

    assert (
        'item.domain_id==="metals"?'
        '(payload.final_action??payload.recommendation??'
        'payload.native_recommendation??null):nativeStatus(item)'
        in recommendations
    )


def test_rec_ui_metals_summary_surfaces_use_certified_monthly_technical_context():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")

    assert 'payloads(detail,"metals_commodity_technical_context")' in javascript
    assert "UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1" in javascript
    assert 'row.universal_asset_id||""' in javascript
    assert '"world_bank"' in javascript
    assert '"monthly"' in javascript
    assert "Daily moving averages are not authorized by the monthly commodity technical-context source." in javascript
    assert "<span>1M return</span>" in javascript
    assert "<span>3M return</span>" in javascript
    assert "<span>6M return</span>" in javascript
    assert "Monthly commodity technical context" in javascript
    assert "MA50 and MA200 are unsupported by monthly source cadence." in javascript
    assert "No interpolation, forward fill, vehicle proxy, or cross-provider imputation is used." in javascript


def test_rec_ui_metals_summary_keeps_uranium_monthly_context_unavailable():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")

    assert 'assetId==="metals:commodity:uranium"' in javascript
    assert "Uranium monthly commodity technical context must remain unavailable under V1." in javascript
    assert "certified EIA source is annual" in javascript
    assert "No vehicle proxy is used." in javascript


def test_rec_ui_metals_summary_no_longer_reads_monthly_returns_from_tactical_state():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")

    assert "t.return_1m_pct" not in javascript
    assert "t.return_3m_pct" not in javascript
    assert "t.return_6m_pct" not in javascript
    assert "t.current_drawdown_pct" not in javascript
