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
        "function renderRefreshStatus(document)",
        "Last certified import",
        "Data age",
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
