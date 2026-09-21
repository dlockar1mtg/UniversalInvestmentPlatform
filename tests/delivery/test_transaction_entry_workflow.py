from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "foundation" / "production" / "dashboard_assets"


def test_guided_transaction_entry_shows_current_and_resulting_position():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    for marker in (
        'id="txn-position-context"',
        'id="txn-current-quantity"',
        'id="txn-current-basis"',
        'id="txn-current-value"',
        'id="txn-preview-quantity"',
        'id="txn-preview-basis"',
        'id="txn-total"',
    ):
        assert marker in html
    assert "function updateTransactionPositionContext()" in javascript
    assert "function syncTransactionAmounts(source)" in javascript
    assert "derivedPortfolioDocument=document" in javascript
    assert 'document.addEventListener("uip:asset-selected",updateTransactionPositionContext)' in javascript


def test_total_trade_amount_can_drive_unit_price_without_changing_ledger_contract():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    assert "Total trade amount" in html
    assert 'transactionTotalDriver="total"' in javascript
    assert "Number(totalInput.value)/quantity" in javascript
    assert 'price_per_unit:$("txn-price").value===""?null:$("txn-price").value' in javascript
    assert 'quantity:$("txn-quantity").value' in javascript


def test_portfolio_can_launch_activity_entry_for_exact_governed_position():
    javascript = (ASSETS / "dashboard.js").read_text(encoding="utf-8")
    picker = (ASSETS / "governed_asset_picker.js").read_text(encoding="utf-8")
    assert "portfolio-add-activity" in javascript
    assert "openPortfolioActivity(button)" in javascript
    assert 'new CustomEvent("uip:select-asset"' in javascript
    assert 'document.addEventListener("uip:select-asset",async event=>' in picker
    assert "Governed asset selected from Portfolio." in picker
    assert 'new CustomEvent("uip:asset-selected"' in picker


def test_advanced_ledger_fields_remain_available_but_out_of_primary_flow():
    html = (ASSETS / "dashboard.html").read_text(encoding="utf-8")
    assert '<details class="wide transaction-advanced">' in html
    for marker in (
        'id="txn-venue"',
        'id="txn-reference"',
        'id="txn-notes"',
        'id="txn-corrects"',
        'id="txn-correction-reason"',
    ):
        assert marker in html


def test_guided_entry_styles_are_responsive():
    css = (ASSETS / "dashboard.css").read_text(encoding="utf-8")
    assert ".txn-position-context{" in css
    assert ".txn-context-grid{" in css
    assert ".transaction-advanced-grid{" in css
    assert "@media(max-width:760px){.txn-context-grid,.transaction-advanced-grid{grid-template-columns:1fr}" in css
