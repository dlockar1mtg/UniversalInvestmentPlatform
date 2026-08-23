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


def test_later_workflows_are_explicit_governed_empty_states_not_mock_financial_values():
    html, _, _ = assets()
    assert "REC-UI-1 reserved" in html
    assert "PORT-1 reserved" in html
    assert "TXN-1 reserved" in html
    assert "REFRESH-UI-1 reserved" in html
    assert "Unknown basis will remain unknown" in html
    assert "does not create transaction records" in html


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
    assert "sessionStorage" in javascript and "localStorage" not in javascript
    assert "dashboard-viewer" not in html and "uiip-dashboard-key" not in html
    assert '"X-API-Key":apiKey' in javascript


def test_empty_stale_loading_and_error_states_are_explicit():
    html, _, javascript = assets()
    assert "No hosted portfolio snapshot is available" in html
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
    assert "@media print" in css and "table{min-width:0}" in css
