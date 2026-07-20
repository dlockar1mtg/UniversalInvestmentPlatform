from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def assets():
    return (
        (ASSETS / "dashboard.html").read_text(encoding="utf-8"),
        (ASSETS / "dashboard.css").read_text(encoding="utf-8"),
        (ASSETS / "dashboard.js").read_text(encoding="utf-8"),
    )


def test_dashboard_contains_portfolio_totals_allocation_positions_and_history():
    html, _, _ = assets()
    for identity in (
        "portfolio-market", "portfolio-cost", "portfolio-gain", "portfolio-allocation",
        "portfolio-positions", "portfolio-history",
    ):
        assert f'id="{identity}"' in html


def test_dashboard_fetches_viewer_protected_current_snapshot_and_history():
    _, _, javascript = assets()
    assert 'optional("/v1/portfolio/snapshots/current")' in javascript
    assert 'optional("/v1/portfolio/snapshots?limit=10")' in javascript
    assert '"X-API-Key":apiKey' in javascript


def test_portfolio_content_is_escaped_and_credential_remains_session_only():
    html, _, javascript = assets()
    assert "snapshot.positions.map" in javascript
    assert "esc(item.name" in javascript and "esc(item.symbol" in javascript
    assert "sessionStorage" in javascript and "localStorage" not in javascript
    assert "dashboard-viewer" not in html and "uiip-dashboard-key" not in html


def test_empty_stale_loading_and_error_states_are_explicit():
    html, _, javascript = assets()
    assert "No hosted portfolio snapshot is available yet" in html
    assert '"Stale":"Ready"' in javascript
    assert "older than 7 days" in javascript
    assert "Loading operational data and portfolio snapshot" in javascript
    assert 'className="message error"' in javascript


def test_gain_loss_and_allocation_are_derived_from_exact_snapshot_values():
    _, _, javascript = assets()
    assert "market-cost" in javascript and "gain/cost*100" in javascript
    assert "item.market_value" in javascript and "item.cost_basis" in javascript
    assert "groups[item.portfolio_group]" in javascript


def test_portfolio_layout_is_responsive_scroll_safe_and_print_safe():
    _, css, _ = assets()
    assert ".table-wrap{overflow-x:auto" in css
    assert "@media(max-width:850px)" in css
    assert ".portfolio-layout{grid-template-columns:1fr}" in css
    assert "@media print" in css and "table{min-width:0}" in css
