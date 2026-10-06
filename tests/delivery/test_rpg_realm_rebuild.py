"""The realm views survive dashboard.js rebuilding the Home or Portfolio page."""

from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets"


def test_realm_pages_are_guarded_against_rebuilds():
    realm = (ASSETS / "rpg_realm.js").read_text(encoding="utf-8")
    assert 'guardRealmPage("portfolio","rpg-treasury",renderInventory,TREASURY_SCROLL)' in realm
    assert 'guardRealmPage("home","rpg-hall",renderHall,HALL_SCROLL)' in realm
    assert "tuck(page,view,TREASURY_SCROLL[0],TREASURY_SCROLL[1]);" in realm
    assert "tuck(page,hall,HALL_SCROLL[0],HALL_SCROLL[1]);" in realm
    # The old one-shot guard skipped re-tucking after renderDerivedPortfolio replaced the page.
    assert 'if(page.classList.contains("rpg-realm-on"))return;' not in realm


def test_portfolio_page_is_still_rebuilt_by_the_dashboard():
    script = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert 'const page=$("portfolio");if(!positions.length){page.innerHTML=' in script
