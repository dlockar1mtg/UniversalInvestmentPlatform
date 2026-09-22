from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def test_home_is_investment_focused_and_uses_actual_portfolio_context():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    for marker in (
        "Your investment dashboard",
        "Portfolio at a glance",
        'id="home-total-value"',
        'id="home-total-basis"',
        'id="home-total-gain"',
        'id="home-position-count"',
        "Record Buy",
        "Record Sell",
        "View Recommendations",
        "Check Data Health",
        "WHAT NEEDS ATTENTION",
        "System & portfolio attention",
    ):
        assert marker in html
    for marker in (
        "function overallPortfolioSnapshot()",
        "function renderHome(presentation,health,refreshDocument)",
        "Certified + external tracked holdings",
        'data-home-page="transactions"',
        'data-home-page="recommendations"',
        'data-home-page="refresh-page"',
        "Portfolio has unpriced positions",
        "Portfolio has incomplete cost basis",
    ):
        assert marker in html or marker in javascript


def test_home_attention_uses_freshness_and_portfolio_coverage_not_universal_rank():
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert 'item.freshness_state==="STALE"' in javascript
    assert 'item.freshness_state==="UNKNOWN"' in javascript
    assert "last-good certified state remains active" in javascript
    assert "The active authority does not publish a governed data-as-of date." in javascript
    assert "universal investment score" not in javascript.lower()
    assert "cross-domain rank" not in javascript.lower()


def test_operations_prioritizes_live_technical_evidence_and_collapses_legacy_snapshot():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    for marker in (
        "Technical evidence & diagnostics",
        "OPS-1 · production evidence",
        'id="ops-api-health"',
        'id="ops-db-health"',
        'id="ops-publication-health"',
        "Active certified publication",
        "Domain registry",
        "Refresh operations",
        "Recent audit activity",
        "API metrics",
        '<details id="legacy-portfolio-reconciliation"',
        "Advanced recovery / legacy reconciliation",
        "setup/reconciliation/recovery",
    ):
        assert marker in html
    for marker in (
        "function renderOperations(presentation,health,summary,refreshDocument)",
        "ops-publication-fingerprint",
        "ops-source-sha",
        "ops-domain-registry",
        "ops-refresh-runs",
        "ops-latest-event",
        "ops-refresh-review",
    ):
        assert marker in javascript


def test_operations_exposes_analytical_authority_separately_from_application_state():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert "Versioned analytical read model" in html
    assert "Current Portfolio ownership is transaction-derived." in html
    assert 'summary?.service?.ready' in javascript
    assert 'presentation?.content_fingerprint' in javascript
    assert 'presentation?.source_database_sha256' in javascript
    assert "refreshDocument?.items" in javascript


def test_home_and_operations_layouts_are_responsive():
    css = (ASSETS / "dashboard.css").read_text(encoding="utf-8")
    for marker in (
        ".home-overview-panel{",
        ".home-quick-actions{",
        ".operations-grid{",
        ".operations-details{",
        ".operations-refresh-row{",
        ".operations-legacy-panel{",
    ):
        assert marker in css
