from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from foundation.portfolio_engine.ledger import LedgerEntry, reconcile_entries
from foundation.portfolio_engine.models import TransactionType


def test_reconciliation_matches_count_and_amount() -> None:
    portfolio_id = uuid4()
    account_id = uuid4()
    entries = [
        LedgerEntry(
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_type=TransactionType.DEPOSIT,
            effective_at=datetime.now(timezone.utc),
            gross_amount=Decimal("1000"),
            fees=Decimal("0"),
            net_amount=Decimal("1000"),
        ),
        LedgerEntry(
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_type=TransactionType.FEE,
            effective_at=datetime.now(timezone.utc),
            gross_amount=Decimal("10"),
            fees=Decimal("0"),
            net_amount=Decimal("-10"),
        ),
    ]
    result = reconcile_entries(
        entries,
        expected_count=2,
        expected_net_amount=Decimal("990"),
    )
    assert result.is_reconciled
