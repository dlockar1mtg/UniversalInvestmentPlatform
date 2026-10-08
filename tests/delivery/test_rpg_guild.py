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
    for heading in ("The Market Board", "The Guild's trials", "Your charter", "Near-identical funds", "Best of each exposure", "Lower official fee (3 years)"):
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


def test_guild_shows_three_year_outlooks_without_ranking_single_funds():
    realm = _read("rpg_realm.js")
    for text in ("The next three years", "Where three years of growth could come from", "Chance of a loss",
                 "TOO CAUTIOUS", "MOVES_FAR_MORE_THAN_ITS_REFERENCE", "Next 3 years, typical"):
        assert text in realm, text
    # owner decision 2026-10-08: single funds may be sorted by the typical figure, always with the caveat
    assert 'st.sort==="p3y"' in realm and "did not pay more in the Guild's trials" in realm
    assert 'sort:"call"' in realm
    css = _read("rpg_theme.css")
    assert ".rpg-outlook-tiles{" in css


def test_guild_gives_every_fund_research_without_new_calls():
    realm = _read("rpg_realm.js")
    for text in ("outlook_3y", "OWN HISTORY", "its own history", "loose_peer_reading", "As a reading only",
                 "missed the real 3-year result by a median of", "it fits loosely", "never compared across funds"):
        assert text in realm, text
    # own-history outlooks never feed the BUY / AVOID call or a fund-level growth sort
    assert "loose_peer_reading.cost_percentile)" not in realm.split("function callText")[1].split("}")[0]


def test_market_board_sorts_by_any_header_and_filters_every_column():
    realm = _read("rpg_realm.js")
    for text in ("data-rpg-sort", "aria-sort", "data-rpg-col=", "data-rpg-num=", "parseNumFilter", "Clear sort and filters",
                 "From 3-year high", "drawdown_3y_high", "blanks last"):
        assert text in realm, text
    assert ".rpg-colfilter-menu{" in _read("rpg_theme.css")
