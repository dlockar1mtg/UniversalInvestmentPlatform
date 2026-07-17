"""Asset-aware stale valuation policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from foundation.portfolio_engine.models import LiquidityTier


DEFAULT_STALE_DAYS = {
    LiquidityTier.DAILY: 3,
    LiquidityTier.WEEKLY: 10,
    LiquidityTier.MONTHLY: 40,
    LiquidityTier.ILLIQUID: 120,
    LiquidityTier.UNKNOWN: 30,
}


@dataclass(slots=True)
class StalePriceResult:
    age_days: int
    stale_after_days: int
    is_stale: bool


def evaluate_staleness(
    valued_at: datetime,
    liquidity_tier: LiquidityTier,
    *,
    as_of: datetime | None = None,
    thresholds: dict[LiquidityTier, int] | None = None,
) -> StalePriceResult:
    reference = as_of or datetime.now(timezone.utc)
    valued = valued_at if valued_at.tzinfo else valued_at.replace(tzinfo=timezone.utc)
    reference = reference if reference.tzinfo else reference.replace(tzinfo=timezone.utc)
    age_days = max(0, (reference - valued).days)
    stale_after = (thresholds or DEFAULT_STALE_DAYS)[liquidity_tier]
    return StalePriceResult(
        age_days=age_days,
        stale_after_days=stale_after,
        is_stale=age_days > stale_after,
    )
