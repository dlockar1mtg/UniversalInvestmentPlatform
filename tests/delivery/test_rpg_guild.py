"""The Merchants' Guild (ETF) realm page and its wiring into the Hall and Treasury."""

from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "foundation" / "production" / "dashboard_assets"


def _read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def test_guild_page_and_tab_are_open():
    html = _read("dashboard.html")
    assert '<button class="nav-item" data-page="guild">' in html
    assert '<section id="guild" class="page"' in html
    realm = _read("rpg_realm.js")
    assert '["etf","Merchants\' Guild \\u00b7 ETFs",\'data-rpg-page="guild"\']' in realm
    assert "is-locked" not in realm and "Opens with the ETF section" not in realm
    script = _read("dashboard.js")
    assert 'guild:"ETFs"' in script and 'guild:"Merchants\' Guild"' in script


def test_guild_reads_the_etf_package_and_stays_read_only():
    realm = _read("rpg_realm.js")
    assert 'api("/v1/presentation/etf")' in realm
    assert "api(`/v1/presentation/etf/${encodeURIComponent(symbol)}`)" in realm
    for heading in ("The Market Board", "The Guild's trials", "Your charter", "Near-identical funds", "Best of each exposure"):
        assert heading in realm, heading
    assert 'h.valuation_source==="ETF_PACKAGE_CLOSE"' in realm
    assert "provisional, not certified" in realm
    for forbidden in ("method:", "eval(", "new Function", "localStorage"):
        assert forbidden not in realm
    assert realm.isascii()


def test_guild_styles_exist():
    css = _read("rpg_theme.css")
    for selector in (".rpg-guild-hero{", ".rpg-guild-table{", ".rpg-fund-pick{", ".rpg-bar.etf>i{", ".rpg-board-filters{"):
        assert selector in css, selector
