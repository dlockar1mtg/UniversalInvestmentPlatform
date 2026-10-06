"""The realm views (rpg_realm.js): wiring, serving and read-only behaviour."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION = ROOT / "foundation" / "production"
ASSETS = PRODUCTION / "dashboard_assets"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_realm_script_is_served_and_loaded_before_the_dashboard():
    html = _read(ASSETS / "dashboard.html")
    realm = html.index('<script src="/dashboard/assets/rpg_realm.js" defer></script>')
    assert realm < html.index('<script src="/dashboard/assets/dashboard.js" defer></script>')
    service = _read(PRODUCTION / "http_service.py")
    assert '@app.get("/dashboard/assets/rpg_realm.js", include_in_schema=False)' in service
    assert 'FileResponse(assets / "rpg_realm.js", media_type="text/javascript")' in service


def test_dashboard_hands_its_data_to_the_realm_views():
    script = _read(ASSETS / "dashboard.js")
    assert 'document.dispatchEvent(new CustomEvent("uip:home-rendered"' in script
    for field in (
        "snapshot,attention,presentation,health",
        "refresh:refreshDocument",
        "portfolio:derivedPortfolioDocument",
        "manualHoldings,externalAccount",
        "transactions:transactionItems",
    ):
        assert field in script
    research = _read(ASSETS / "recommendation_ui.js")
    assert 'new CustomEvent("uip:crypto-detail",{detail:{page,item,payload:cvV2Decision(item)}})' in research
    assert 'document.addEventListener("uip:open-research"' in research


def test_realm_module_listens_and_stays_read_only():
    realm = _read(ASSETS / "rpg_realm.js")
    assert 'document.addEventListener("uip:home-rendered"' in realm
    assert 'document.addEventListener("uip:crypto-detail"' in realm
    assert "/v1/presentation/recommendation-catalog?domain=" in realm
    for forbidden in ("method:", "eval(", "new Function", "localStorage", "innerHTML=d", "<style"):
        assert forbidden not in realm, forbidden
    assert realm.isascii()


def test_realm_views_cover_the_three_mockup_screens():
    realm = _read(ASSETS / "rpg_realm.js")
    for heading in (
        "The Universal Ledger",
        "Quest Journal",
        "Recent deeds",
        "The Treasury",
        "Inventory",
        "The Rune of Value",
        "The Long Road",
        "The Scrying Pool",
        "Omen of the week",
        "Your hoard",
    ):
        assert heading in realm, heading
    css = _read(ASSETS / "rpg_theme.css")
    for selector in (".rpg-chronicle", ".rpg-ring", ".rpg-slot", ".rpg-vault-hero", ".rpg-scroll", ".rpg-vault-on>.metals-hero"):
        assert selector in css, selector
    assert "button:not(.secondary):not(.nav-item):not(.slot):not(.rpg-btn)" in css
