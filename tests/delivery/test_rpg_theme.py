"""The fantasy-RPG dashboard theme: loading order, fonts, CSP and navigation labels."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION = ROOT / "foundation" / "production"
ASSETS = PRODUCTION / "dashboard_assets"

NAV = (
    ("home", "The Hall", "Home"),
    ("recommendations", "Counsel", "Recommendations"),
    ("portfolio", "The Treasury", "Portfolio"),
    ("transactions", "Book of Deeds", "Transactions"),
    ("refresh-page", "Vitals", "Refresh"),
    ("operations", "The Workshop", "Operations"),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_theme_stylesheet_loads_after_the_base_stylesheets():
    html = _read(ASSETS / "dashboard.html")
    theme = html.index('href="/dashboard/assets/rpg_theme.css"')
    for base in ("dashboard.css", "recommendation_visual.css", "metals_visual.css"):
        assert html.index(f'href="/dashboard/assets/{base}"') < theme
    assert 'href="https://fonts.googleapis.com/css2?family=Alegreya' in html
    assert "<strong>The Universal Ledger</strong>" in html


def test_theme_stylesheet_is_served_and_self_contained():
    service = _read(PRODUCTION / "http_service.py")
    assert '@app.get("/dashboard/assets/rpg_theme.css", include_in_schema=False)' in service
    assert 'FileResponse(assets / "rpg_theme.css", media_type="text/css")' in service
    css = _read(ASSETS / "rpg_theme.css")
    assert "--font-display" in css
    assert "url(" not in css


def test_csp_opens_only_the_font_hosts():
    security = _read(PRODUCTION / "live_security.py")
    assert "style-src 'self' https://fonts.googleapis.com;" in security
    assert "font-src 'self' https://fonts.gstatic.com;" in security
    assert "script-src 'self';" in security
    assert "'unsafe-inline'" not in security


def test_dashboard_markup_stays_free_of_inline_styles():
    html = _read(ASSETS / "dashboard.html")
    assert "<style" not in html
    assert " style=" not in html


def test_navigation_keeps_page_ids_and_plain_labels():
    html = _read(ASSETS / "dashboard.html")
    for page_id, realm, plain in NAV:
        assert f'data-page="{page_id}"><span class="nav-realm">{realm}</span><small>{plain}</small></button>' in html
    script = _read(ASSETS / "dashboard.js")
    assert "const realmTitles=" in script
    for page_id, realm, _plain in NAV:
        key = f'"{page_id}"' if "-" in page_id else page_id
        assert f'{key}:"{realm}"' in script


def test_old_teal_palette_is_retired():
    for name in ("dashboard.css", "recommendation_visual.css", "metals_visual.css", "recommendation_ui.js", "metals_vehicle_ui.js"):
        text = _read(ASSETS / name)
        assert "#63e6be" not in text.lower(), name
        assert "99,230,190" not in text.replace(" ", ""), name
