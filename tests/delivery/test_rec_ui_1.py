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

    # Only the native helper declaration and the non-Metals delegation
    # may directly use nativeStatus after deployment.
    assert javascript.count("nativeStatus(") == 2
    assert javascript.count("displayStatus(") >= 4

    # Existing domain-native contracts are retained.
    assert (
        'item.domain_id==="mtg"?(payload.native_purchase_status??null):(payload.native_recommendation??payload.recommendation??null)'
        in javascript
    )

    def displayed_status(domain_id, payload):
        if domain_id == "metals":
            return (
                payload.get("final_action")
                or payload.get("recommendation")
                or payload.get("native_recommendation")
            )

        if domain_id == "mtg":
            return payload.get("native_purchase_status")

        return (
            payload.get("native_recommendation")
            or payload.get("recommendation")
        )

    metals_cases = {
        "metals:commodity:gold":
            ("HOLD", "RANKED_OPPORTUNITY"),
        "metals:commodity:uranium":
            ("HOLD", "RANKED_OPPORTUNITY"),
        "metals:vehicle:BIL":
            ("REFERENCE_CONTROL", "RESERVE_BUY"),
        "metals:vehicle:COPX":
            ("HOLD", "HOLD"),
        "metals:vehicle:CPER":
            ("HOLD", "HOLD"),
        "metals:vehicle:GLD":
            ("WATCH", "BUY"),
        "metals:vehicle:IAU":
            ("WATCH", "BUY"),
        "metals:vehicle:PPLT":
            ("WATCH", "BUY"),
        "metals:vehicle:SGOL":
            ("WATCH", "BUY"),
        "metals:vehicle:SIVR":
            ("WATCH", "BUY"),
        "metals:vehicle:SLV":
            ("WATCH", "BUY"),
        "metals:vehicle:URA":
            ("HOLD", "HOLD"),
    }

    for asset_id, (
        final_action,
        native_recommendation,
    ) in metals_cases.items():
        payload = {
            "final_action":
                final_action,
            "recommendation":
                final_action,
            "native_recommendation":
                native_recommendation,
        }

        assert (
            displayed_status(
                "metals",
                payload,
            )
            == final_action
        ), asset_id

    assert displayed_status(
        "crypto",
        {
            "final_action": "WATCH",
            "recommendation": "WATCH",
            "native_recommendation": "BUY",
        },
    ) == "BUY"

    assert displayed_status(
        "mtg",
        {
            "final_action": "HOLD",
            "recommendation": "HOLD",
            "native_purchase_status":
                "PURCHASE_CANDIDATE",
        },
    ) == "PURCHASE_CANDIDATE"

def test_rec_ui_metals_final_action_labels_distinguish_governed_and_native_semantics():
    javascript = read("foundation/production/dashboard_assets/recommendation_ui.js")

    assert (
        'function statusFilterLabel(domain){return domain==="metals"?"Decision status":"Native status"}'
        in javascript
    )
    assert (
        'function statusFilterAllLabel(domain){return domain==="metals"?"All decision statuses":"All native statuses"}'
        in javascript
    )
    assert (
        'function recommendationColumnLabel(domain){return domain==="metals"?"Final decision":"Native recommendation"}'
        in javascript
    )

    assert (
        'item.domain_id==="metals"?(payload.final_action??payload.recommendation??payload.native_recommendation??null):nativeStatus(item)'
        in javascript
    )

    old_metals_sequence = (
        '<div class="rec-narrative">'
        '<div><span>Native recommendation</span>'
        '<p>${escapeHtml(cleanStatus(displayStatus(item)))}</p></div>'
        '<div><span>Rationale</span>'
        '<p>${escapeHtml(recommendation.rationale??"No rationale is populated.")}</p></div>'
        '<div><span>Risk summary</span>'
    )

    corrected_metals_sequence = (
        '<div class="rec-narrative">'
        '<div><span>Final decision</span>'
        '<p>${escapeHtml(cleanStatus(displayStatus(item)))}</p></div>'
        '<div><span>Native recommendation</span>'
        '<p>${escapeHtml(cleanStatus(recommendation.native_recommendation??"MISSING"))}</p></div>'
        '<div><span>Rationale</span>'
        '<p>${escapeHtml(recommendation.rationale??"No rationale is populated.")}</p></div>'
        '<div><span>Risk summary</span>'
    )

    assert old_metals_sequence not in javascript
    assert corrected_metals_sequence in javascript

    assert (
        '${escapeHtml(statusFilterAllLabel(selectedDomain))}'
        in javascript
    )
    assert (
        '${escapeHtml(statusFilterLabel(selectedDomain))}'
        in javascript
    )
    assert (
        '${escapeHtml(recommendationColumnLabel(selectedDomain))}'
        in javascript
    )

    # Non-Metals native semantics remain unchanged.
    assert (
        'item.domain_id==="mtg"?(payload.native_purchase_status??null):(payload.native_recommendation??payload.recommendation??null)'
        in javascript
    )
