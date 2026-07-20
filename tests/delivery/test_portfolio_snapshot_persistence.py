from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sqlite3

import pytest

from foundation.production.portfolio import PortfolioPosition
from foundation.production.portfolio_persistence import (
    SQLitePortfolioSnapshotRepository,
    create_portfolio_snapshot,
)


NOW = datetime(2026, 7, 20, 18, 0, tzinfo=timezone.utc)


def position(position_id="p1", value="125.50", *, currency="USD"):
    return PortfolioPosition(
        position_id, "primary", "etf", "etf", position_id, Decimal("1.25"),
        Decimal("100.25"), Decimal(value), currency, NOW, position_id.upper(),
        f"Position {position_id}", position_id.upper(), None, "liquid", "",
    )


def repository():
    result = SQLitePortfolioSnapshotRepository(sqlite3.connect(":memory:"))
    result.initialize()
    return result


def test_snapshot_is_order_invariant_and_reconciles_exact_totals():
    first = create_portfolio_snapshot((position("p2", "200.75"), position("p1")), imported_at=NOW)
    second = create_portfolio_snapshot(tuple(reversed(first.positions)), imported_at=NOW + timedelta(hours=1))
    assert first.fingerprint == second.fingerprint
    assert first.snapshot_id == second.snapshot_id
    assert tuple(item.position_id for item in first.positions) == ("p1", "p2")
    assert first.total_cost_basis == Decimal("200.50")
    assert first.total_market_value == Decimal("326.25")


def test_repository_round_trips_snapshot_without_decimal_or_metadata_loss():
    store = repository()
    snapshot = create_portfolio_snapshot((position(),), imported_at=NOW, metadata={"source": "hosted-import"})
    loaded = store.save(snapshot)
    assert loaded == snapshot
    assert store.get(snapshot.snapshot_id) == snapshot
    assert dict(store.get(snapshot.snapshot_id).metadata) == {"source": "hosted-import"}


def test_identical_content_is_idempotent_and_does_not_duplicate_history():
    store = repository()
    first = create_portfolio_snapshot((position(),), imported_at=NOW)
    duplicate = create_portfolio_snapshot((position(),), imported_at=NOW + timedelta(days=1))
    assert store.save(first) == first
    assert store.save(duplicate) == first
    assert len(store.history()) == 1


def test_changed_content_creates_history_and_latest_is_deterministic():
    store = repository()
    older = create_portfolio_snapshot((position(value="125.50"),), imported_at=NOW)
    newer = create_portfolio_snapshot((position(value="130.00"),), imported_at=NOW + timedelta(days=1))
    store.save(older)
    store.save(newer)
    assert store.latest() == newer
    assert store.history() == (newer, older)


def test_snapshot_rejects_mixed_currency_naive_time_and_empty_positions():
    with pytest.raises(ValueError, match="at least one"):
        create_portfolio_snapshot(())
    with pytest.raises(ValueError, match="one currency"):
        create_portfolio_snapshot((position("p1"), position("p2", currency="CAD")))
    with pytest.raises(ValueError, match="timezone-aware"):
        create_portfolio_snapshot((position(),), imported_at=datetime(2026, 7, 20))


def test_history_bounds_and_missing_identity_are_explicit():
    store = repository()
    assert store.latest() is None
    with pytest.raises(KeyError):
        store.get("missing")
    with pytest.raises(ValueError, match="between 1 and 100"):
        store.history(0)
