from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_metals_premium_styles_are_served_as_same_origin_static_css():
    html = read("foundation/production/dashboard_assets/dashboard.html")
    service = read("foundation/production/http_service.py")
    css = read("foundation/production/dashboard_assets/metals_visual.css")

    assert '<link rel="stylesheet" href="/dashboard/assets/metals_visual.css">' in html
    assert '@app.get("/dashboard/assets/metals_visual.css"' in service
    assert 'FileResponse(assets / "metals_visual.css", media_type="text/css")' in service

    for selector in (
        ".metals-layout",
        ".metals-card-grid",
        ".metals-card",
        ".metals-momentum",
        ".metals-regime-track",
        ".metals-explainer",
        ".metals-hero",
        ".metals-detail-grid",
        ".metals-panel",
        ".metals-momentum-bars",
    ):
        assert selector in css


def test_hosted_csp_allows_same_origin_styles_but_not_inline_style_blocks():
    security = read("foundation/production/live_security.py")
    assert "style-src 'self'" in security
    assert "'unsafe-inline'" not in security

    # The served Metals stylesheet must therefore be loaded from the dashboard origin.
    html = read("foundation/production/dashboard_assets/dashboard.html")
    assert "/dashboard/assets/metals_visual.css" in html


def test_dashboard_scripts_never_write_inline_style_attributes_or_style_elements():
    """The CSP blocks both; per-element styles travel as data-css and are applied through the CSSOM."""
    assets = ROOT / "foundation/production/dashboard_assets"
    for script in sorted(assets.glob("*.js")):
        text = script.read_text(encoding="utf-8")
        assert ' style="' not in text, script.name
        assert 'createElement("style")' not in text, script.name
    realm = (assets / "rpg_realm.js").read_text(encoding="utf-8")
    assert 'el.style.cssText=el.getAttribute("data-css")' in realm and "new MutationObserver" in realm
