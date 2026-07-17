from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from foundation.portfolio_engine.ledger import LedgerEntry, verify_audit_hash
from foundation.portfolio_engine.models import AssetCategory, TransactionType


def test_buy_entry_calculates_negative_cash_flow_and_hash() -> None:
    entry = LedgerEntry(
        portfolio_id=uuid4(),
        account_id=uuid4(),
        transaction_type=TransactionType.BUY,
        effective_at=datetime.now(timezone.utc),
        asset_id="BTC",
        asset_name="Bitcoin",
        asset_category=AssetCategory.CRYPTO,
        quantity=Decimal("0.02"),
        unit_price=Decimal("50000"),
        gross_amount=Decimal("1000"),
        fees=Decimal("5"),
        net_amount=Decimal("-1005"),
    )
    assert entry.net_amount == Decimal("-1005")
    assert len(entry.audit_hash) == 64
    assert verify_audit_hash(entry)


def test_buy_entry_rejects_incorrect_net_amount() -> None:
    with pytest.raises(ValueError, match="does not match"):
        LedgerEntry(
            portfolio_id=uuid4(),
            account_id=uuid4(),
            transaction_type=TransactionType.BUY,
            effective_at=datetime.now(timezone.utc),
            asset_id="BTC",
            quantity=Decimal("0.02"),
            unit_price=Decimal("50000"),
            gross_amount=Decimal("1000"),
            fees=Decimal("5"),
            net_amount=Decimal("-1000"),
        )
