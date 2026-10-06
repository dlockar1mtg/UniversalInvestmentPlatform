"""Counsel realm bar and readable row, card and tab buttons in the RPG theme."""

from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets"


def _read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_research_views_get_a_realm_bar():
    realm = _read("rpg_realm.js")
    assert "function decorateCounsel()" in realm
    assert ".observe(page,{childList:true})" in realm
    assert 'realmTabs(domain||"counsel")' in realm
    assert '${realmTabs("crypto")}<section class="rpg-stone rpg-vault-hero">' in realm


def test_omen_only_for_coins_with_a_seven_day_model():
    realm = _read("rpg_realm.js")
    assert 'p.model_short_term||key==="bitcoin"||key==="ethereum"?vaultOmen(p):""' in realm


def test_rows_cards_and_tabs_are_not_painted_gold():
    css = _read("rpg_theme.css")
    exclusions = ':not([class*="-row"]):not([class*="-card"]):not([class*="-tab"])'
    assert f"button:not(.secondary):not(.nav-item):not(.slot):not(.rpg-btn){exclusions}{{" in css
    assert 'button[class*="-tab"]:not(.rpg-btn).active' in css
    assert ".rpg-counsel-bar{" in css
