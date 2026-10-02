from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def test_refresh_page_exposes_operational_health_and_lifecycle():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    css = (ASSETS / "dashboard.css").read_text(encoding="utf-8")
    for marker in (
        "Can I trust the displayed data right now?",
        'id="refresh-healthy-count"',
        'id="refresh-review-count"',
        'id="refresh-health-reload"',
        'id="refresh-lifecycle"',
        "Failed cycles never replace the last-good certified state",
    ):
        assert marker in html
    for marker in (
        'request("/v1/refresh/status")',
        "function renderRefreshStatus(refreshDocument)",
        "Last certified import",
        "Data age",
        "Monthly source data",
        '"Daily cadence"} · stale after ${item.freshness_max_age_days} days',
        "OPS ${esc(item.health_state)}",
        "DATA ${esc(freshness)}",
        "Operational health",
        "Freshness",
        "Next scheduled run",
        "Current package",
        "Authority version",
        "Last failure",
        "Last-good state",
        "Manual dispatch not exposed in hosted UI",
    ):
        assert marker in javascript
    assert ".refresh-domain-cards{" in css
    assert ".refresh-lifecycle{" in css
    assert ".pill.warn{" in css
    assert ".refresh-domain-pills{" in css


def test_refresh_page_does_not_misrepresent_refresh_as_retraining_or_local_collection():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert "Refresh is source-owned and separate from model retraining." in html
    assert "SOURCE_OWNED" not in html
    assert "manual source-workflow dispatch is not yet exposed here" in html
    assert "Manual refresh available" in javascript
    assert "Manual dispatch not exposed in hosted UI" in javascript


def test_refresh_renderer_does_not_shadow_browser_document_object():
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert "function renderRefreshStatus(refreshDocument)" in javascript
    assert "function renderRefreshStatus(document)" not in javascript
    assert 'document.querySelectorAll(".refresh-domain-reload")' in javascript


def test_refresh_summary_counts_stale_unknown_or_unhealthy_domains_for_review():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert "Freshness review" in html
    assert "Stale, unknown, or operationally unhealthy" in html
    assert "freshness_review_count" in javascript
    assert 'freshness==="STALE"?"bad":"warn"' in javascript
