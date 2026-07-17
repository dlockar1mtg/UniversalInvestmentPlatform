from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from foundation.portfolio_engine.ledger import LedgerEntry
from foundation.portfolio_engine.models import TransactionType
from foundation.portfolio_engine.positions import calculate_cash_balances


def test_cash_balance_sums_net_ledger_flows() -> None:
    portfolio_id = uuid4()
    account_id = uuid4()
    entries = [
        LedgerEntry(
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_type=TransactionType.DEPOSIT,
            effective_at=datetime.now(timezone.utc),
            gross_amount=Decimal("3000"),
            net_amount=Decimal("3000"),
        ),
        LedgerEntry(
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_type=TransactionType.BUY,
            effective_at=datetime.now(timezone.utc),
            asset_id="VOO",
            quantity=Decimal("2"),
            unit_price=Decimal("500"),
            gross_amount=Decimal("1000"),
            fees=Decimal("1"),
            net_amount=Decimal("-1001"),
        ),
    ]
    balances = calculate_cash_balances(entries)
    assert balances[(account_id, "USD")] == Decimal("1999")
