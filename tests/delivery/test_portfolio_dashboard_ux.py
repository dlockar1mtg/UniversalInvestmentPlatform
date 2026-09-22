from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def assets():
    return (
        (ASSETS / "dashboard.html").read_text(encoding="utf-8"),
        (ASSETS / "dashboard.css").read_text(encoding="utf-8"),
        (ASSETS / "dashboard.js").read_text(encoding="utf-8"),
    )


def test_dashboard_contains_approved_six_screen_shell_and_persistent_status():
    html, _, _ = assets()
    for identity in (
        "home", "recommendations", "portfolio", "transactions", "refresh-page", "operations",
        "global-status-text", "global-refresh", "global-publication",
    ):
        assert f'id="{identity}"' in html
    for label in ("Home", "Recommendations", "Portfolio", "Transactions", "Refresh", "Operations"):
        assert label in html


def test_dashboard_home_uses_certified_presentation_status_and_domain_health():
    _, _, javascript = assets()
    assert 'request("/v1/presentation/status")' in javascript
    assert 'request("/v1/presentation/domain-health")' in javascript
    assert "Certified authority active" in javascript
    assert "source_database_sha256" in javascript
    assert "content_fingerprint" in javascript


def test_remaining_reserved_workflows_are_explicit_while_txn_portfolio_and_rec_ui_are_real():
    html, _, javascript = assets()
    assert "REC-UI-1 · certified catalog" in html
    assert "REC-UI-1 reserved" not in html
    assert "REFRESH-UI-1 · observability" in html
    assert "REFRESH-UI-1 reserved" not in html
    assert 'request("/v1/refresh/status")' in javascript
    assert "TXN-1 · guided entry + retained ledger" in html
    assert "append-only application state" in html.lower()
    assert 'id="transaction-form"' in html
    assert 'request("/v1/transactions"' in javascript
    assert "corrects_transaction_id" in javascript
    assert 'request("/v1/portfolio/enriched")' in javascript
    assert "PORT-1 · transaction-derived" in javascript
    assert "renderDerivedPortfolio" in javascript
    assert '/dashboard/assets/recommendation_ui.js' in html


def test_transaction_derived_portfolio_exposes_v7_kpis_and_holdings_contract():
    _, _, javascript = assets()
    for marker in (
        "Market value",
        "Cost basis",
        "Unrealized P/L",
        "Realized P/L",
        "Total return",
        "Positions",
        "Allocation by domain",
        "Pricing coverage",
        "Basis coverage",
        "Current price",
        "Market value",
        "Model status",
        "Last updated",
    ):
        assert marker in javascript
    assert "item.asset_name||item.asset_id" in javascript
    assert "item.asset_subclass" in javascript
    assert "item.recommendation" in javascript
    assert "item.freshness" in javascript
    assert "document.effective_transaction_count" in javascript
    assert "document.superseded_transaction_count" in javascript


def test_transaction_derived_portfolio_preserves_missing_and_currency_semantics():
    _, _, javascript = assets()
    assert 'item.current_price==null?"Unpriced"' in javascript
    assert 'item.cost_basis==null?"Unknown"' in javascript
    assert "Requires complete price + basis coverage" in javascript
    assert "governed FX conversion layer" in javascript
    assert "currencies.length===1" in javascript
    assert "Allocation unavailable until UIP has a governed FX conversion layer" in javascript


def test_acorns_external_account_renders_with_populated_transaction_portfolio():
    _, _, javascript = assets()
    assert "function renderExternalAccount(document)" in javascript
    assert 'renderExternalAccount(externalAccount)' in javascript
    assert 'renderManualHoldings(manualHoldings)' in javascript
    assert 'page.querySelector(".external-account-panel")?.remove()' in javascript
    assert "Acorns · manual snapshot" in javascript
    assert 'request("/v1/external-accounts/performance"' in javascript


def test_dashboard_preserves_legacy_operations_portfolio_for_reconciliation_only():
    html, _, javascript = assets()
    for identity in (
        "portfolio-market", "portfolio-cost", "portfolio-gain", "portfolio-allocation",
        "portfolio-positions", "portfolio-history",
    ):
        assert f'id="{identity}"' in html
    assert "setup/reconciliation/recovery" in html
    assert 'optional("/v1/portfolio/snapshots/current")' in javascript
    assert 'optional("/v1/portfolio/snapshots?limit=10")' in javascript


def test_portfolio_content_is_escaped_and_credential_remains_session_only():
    html, _, javascript = assets()
    assert "snapshot.positions.map" in javascript
    assert "esc(item.name" in javascript and "esc(item.symbol" in javascript
    assert "esc(item.asset_name||item.asset_id)" in javascript
    assert "sessionStorage" in javascript and "localStorage" not in javascript
    assert "dashboard-viewer" not in html and "uiip-dashboard-key" not in html
    assert '"X-API-Key":apiKey' in javascript


def test_transaction_content_is_escaped_and_unknown_price_is_not_zero():
    _, _, javascript = assets()
    assert "renderTransactions" in javascript
    assert "esc(item.asset_id)" in javascript
    assert "Price unknown" in javascript
    assert 'price_per_unit:$("txn-price").value===""?null' in javascript


def test_empty_stale_loading_and_error_states_are_explicit():
    html, _, javascript = assets()
    assert "No hosted portfolio snapshot is available" in html
    assert "No transactions have been recorded yet" in html
    assert "No transaction-derived holdings yet" in javascript
    assert "Portfolio accounting is blocked" in javascript
    assert '"Stale":"Ready"' in javascript
    assert "older than 7 days" in javascript
    assert "Loading certified presentation authority" in javascript
    assert 'className="message error"' in javascript


def test_gain_loss_and_allocation_are_derived_from_exact_legacy_snapshot_values():
    _, _, javascript = assets()
    assert "market-cost" in javascript and "gain/cost*100" in javascript
    assert "item.market_value" in javascript and "item.cost_basis" in javascript
    assert "groups[item.portfolio_group]" in javascript


def test_dashboard_layout_is_responsive_scroll_safe_and_print_safe():
    _, css, _ = assets()
    assert ".table-wrap{overflow-x:auto" in css
    assert "@media(max-width:760px)" in css
    assert ".portfolio-layout{grid-template-columns:1fr}" in css
    assert ".transaction-form{grid-template-columns:1fr}" in css
    assert "@media print" in css and "table{min-width:0}" in css
