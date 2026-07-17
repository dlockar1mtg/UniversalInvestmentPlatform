from datetime import datetime, timezone

from foundation.portfolio_engine.models import LiquidityTier
from foundation.portfolio_engine.valuations import evaluate_staleness


def test_daily_price_becomes_stale_after_three_days() -> None:
    result = evaluate_staleness(
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        LiquidityTier.DAILY,
        as_of=datetime(2026, 1, 5, tzinfo=timezone.utc),
    )
    assert result.age_days == 4
    assert result.is_stale


def test_illiquid_price_remains_current_longer() -> None:
    result = evaluate_staleness(
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        LiquidityTier.ILLIQUID,
        as_of=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    assert not result.is_stale
