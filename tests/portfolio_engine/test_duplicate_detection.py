from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from foundation.portfolio_engine.ledger import LedgerEntry, split_duplicates
from foundation.portfolio_engine.models import AssetCategory, TransactionType


def _entry(source_record_id: str) -> LedgerEntry:
    return LedgerEntry(
        portfolio_id=uuid4(),
        account_id=uuid4(),
        transaction_type=TransactionType.BUY,
        effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        asset_id="BTC",
        asset_category=AssetCategory.CRYPTO,
        quantity=Decimal("0.01"),
        unit_price=Decimal("50000"),
        gross_amount=Decimal("500"),
        fees=Decimal("0"),
        net_amount=Decimal("-500"),
        source_platform="test",
        source_record_id=source_record_id,
    )


def test_duplicate_source_record_is_rejected() -> None:
    first = _entry("row-1")
    second = _entry("row-1")
    result = split_duplicates([first, second])
    assert len(result.accepted) == 1
    assert len(result.duplicates) == 1
