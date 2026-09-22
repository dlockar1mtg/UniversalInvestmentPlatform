from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from foundation.production.manual_holdings import (
    SQLiteManualHoldingRepository,
    create_manual_holding_snapshot,
)


def snapshot(**overrides):
    values = dict(
        symbol="voo",
        asset_name="Vanguard S&P 500 ETF",
        asset_type="ETF",
        account_id="brokerage",
        as_of=datetime(2026, 9, 22, 12, tzinfo=timezone.utc),
        shares=Decimal("3.5"),
        cost_basis=Decimal("1500"),
        current_value=Decimal("1625"),
        recorded_by="operator",
        recorded_at=datetime(2026, 9, 22, 13, tzinfo=timezone.utc),
    )
    values.update(overrides)
    return create_manual_holding_snapshot(**values)


def test_manual_holding_derives_position_metrics():
    item = snapshot()
    assert item.symbol == "VOO"
    assert item.gain_loss == Decimal("125")
    assert item.return_pct == Decimal("8.333333333333333333333333333")
    assert item.average_cost == Decimal("428.5714285714285714285714286")
    assert item.current_price == Decimal("464.2857142857142857142857143")
    assert item.authority_state == "MANUAL_USER_ENTERED_EXTERNAL_HOLDING"


def test_manual_holding_requires_stock_or_etf_and_non_negative_values():
    with pytest.raises(ValueError, match="ETF or STOCK"):
        snapshot(asset_type="CRYPTO")
    with pytest.raises(ValueError, match="non-negative"):
        snapshot(current_value=Decimal("-1"))


def test_repository_current_uses_latest_snapshot_per_symbol_and_account():
    db = sqlite3.connect(":memory:")
    repository = SQLiteManualHoldingRepository(db)
    repository.initialize()
    first = snapshot(current_value=Decimal("1600"))
    later = snapshot(
        as_of=datetime(2026, 9, 23, 12, tzinfo=timezone.utc),
        current_value=Decimal("1700"),
        recorded_at=datetime(2026, 9, 23, 13, tzinfo=timezone.utc),
    )
    second_symbol = snapshot(
        symbol="QQQ",
        asset_name="Invesco QQQ Trust",
        shares=Decimal("1.2"),
        cost_basis=Decimal("500"),
        current_value=Decimal("540"),
    )
    repository.save(first)
    repository.save(later)
    repository.save(second_symbol)
    items = repository.current()
    assert [(item.symbol, item.current_value) for item in items] == [
        ("QQQ", Decimal("540")),
        ("VOO", Decimal("1700")),
    ]
    assert len(repository.history("VOO", "brokerage")) == 2


def test_repository_save_is_idempotent_by_fingerprint():
    db = sqlite3.connect(":memory:")
    repository = SQLiteManualHoldingRepository(db)
    repository.initialize()
    item = snapshot()
    assert repository.save(item).snapshot_id == item.snapshot_id
    assert repository.save(item).snapshot_id == item.snapshot_id
    assert len(repository.history("VOO", "brokerage")) == 1
