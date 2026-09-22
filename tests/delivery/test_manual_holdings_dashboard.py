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
