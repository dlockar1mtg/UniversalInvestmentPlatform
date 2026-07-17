from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from foundation.portfolio_engine.ledger import LedgerEntry
from foundation.portfolio_engine.models import AssetCategory, TransactionType
from foundation.portfolio_engine.positions import build_positions


def test_position_builder_derives_quantity_and_cost_basis() -> None:
    portfolio_id = uuid4()
    account_id = uuid4()
    entries = [
        LedgerEntry(
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_type=TransactionType.BUY,
            effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            asset_id="BTC",
            asset_name="Bitcoin",
            asset_category=AssetCategory.CRYPTO,
            quantity=Decimal("1"),
            unit_price=Decimal("40000"),
            gross_amount=Decimal("40000"),
            net_amount=Decimal("-40000"),
        ),
        LedgerEntry(
            portfolio_id=portfolio_id,
            account_id=account_id,
            transaction_type=TransactionType.BUY,
            effective_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            asset_id="BTC",
            asset_name="Bitcoin",
            asset_category=AssetCategory.CRYPTO,
            quantity=Decimal("1"),
            unit_price=Decimal("60000"),
            gross_amount=Decimal("60000"),
            net_amount=Decimal("-60000"),
        ),
    ]
    positions = build_positions(
        entries,
        as_of=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    assert len(positions) == 1
    assert positions[0].quantity == Decimal("2")
    assert positions[0].average_unit_cost == Decimal("50000")
