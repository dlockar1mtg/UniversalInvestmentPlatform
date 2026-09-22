from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def test_portfolio_supports_manual_stock_and_etf_holdings():
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    css = (ASSETS / "dashboard.css").read_text(encoding="utf-8")
    for marker in (
        "Manual brokerage holdings",
        "Stocks & ETFs · user-entered snapshots",
        'id="manual-symbol"',
        'id="manual-asset-type"',
        'id="manual-shares"',
        'id="manual-cost-basis"',
        'id="manual-current-value"',
        'request("/v1/manual-holdings"',
        "renderManualHoldings(manualHoldings)",
    ):
        assert marker in javascript
    assert ".manual-holdings-panel{" in css
    assert ".manual-holdings-table{" in css


def test_manual_holdings_are_explicitly_separate_from_certified_port1_totals():
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert "remain separate from certified PORT-1 totals" in javascript
    assert "MANUAL" not in javascript.split("function renderDerivedPortfolio(document)", 1)[0]


def test_portfolio_exposes_unified_all_account_overview():
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    css = (ASSETS / "dashboard.css").read_text(encoding="utf-8")
    for marker in (
        "function renderOverallPortfolioOverview()",
        "Overall portfolio",
        "Certified holdings + Acorns + manual stocks & ETFs",
        "Total current value",
        "Total cost basis",
        "Total gain / loss",
        "Overall return",
        "Overall allocation",
        "Included sources",
        "Certified PORT-1",
        "Manual stocks & ETFs",
        "Acorns",
        "renderOverallPortfolioOverview()",
    ):
        assert marker in javascript
    assert ".overall-portfolio-panel{" in css
    assert ".overall-portfolio-layout{" in css


def test_unified_overview_combines_values_without_erasing_source_authority():
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert "const totalValue=coreMarket+acornsValue+manualValue" in javascript
    assert "const totalBasis=coreBasis+acornsBasis+manualBasis" in javascript
    assert "const totalGain=totalValue-totalBasis" in javascript
    assert "Mixed-authority personal summary" in javascript
    assert "each underlying section keeps its own authority" in javascript
    assert 'allocation["Stocks & ETFs"]' in javascript
    assert 'allocation["Acorns"]' in javascript
