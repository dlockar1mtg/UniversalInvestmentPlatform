"""Select the best usable valuation by recency and source priority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from foundation.portfolio_engine.models import (
    LiquidityTier,
    Valuation,
    ValuationConfidence,
    ValuationSource,
)

from .stale_price_policy import evaluate_staleness


SOURCE_PRIORITY = {
    ValuationSource.MARKET: 5,
    ValuationSource.PLATFORM: 4,
    ValuationSource.APPRAISAL: 3,
    ValuationSource.MODEL: 2,
    ValuationSource.MANUAL: 1,
}


@dataclass(slots=True)
class SelectedValuation:
    asset_id: str
    account_id: UUID | None
    price: Decimal
    currency: str
    valued_at: datetime
    source: ValuationSource
    confidence: ValuationConfidence
    source_reference: str | None
    age_days: int
    is_stale: bool


def select_valuation(
    valuations: list[Valuation],
    *,
    liquidity_tier: LiquidityTier,
    as_of: datetime,
) -> SelectedValuation | None:
    candidates = [valuation for valuation in valuations if valuation.valued_at <= as_of]
    if not candidates:
        return None

    # Recency is primary. Source priority breaks ties at the same timestamp.
    selected = max(
        candidates,
        key=lambda valuation: (
            valuation.valued_at,
            SOURCE_PRIORITY[valuation.source],
            valuation.confidence.value,
        ),
    )
    stale = evaluate_staleness(
        selected.valued_at,
        liquidity_tier,
        as_of=as_of,
    )
    return SelectedValuation(
        asset_id=selected.asset_id,
        account_id=selected.account_id,
        price=selected.price,
        currency=selected.currency,
        valued_at=selected.valued_at,
        source=selected.source,
        confidence=selected.confidence,
        source_reference=selected.source_reference,
        age_days=stale.age_days,
        is_stale=stale.is_stale,
    )
