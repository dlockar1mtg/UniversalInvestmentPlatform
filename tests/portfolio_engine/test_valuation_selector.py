from datetime import datetime, timezone
from decimal import Decimal

from foundation.portfolio_engine.models import (
    LiquidityTier,
    Valuation,
    ValuationConfidence,
    ValuationSource,
)
from foundation.portfolio_engine.valuations import select_valuation


def test_newer_platform_value_beats_older_market_value() -> None:
    valuations = [
        Valuation(
            asset_id="MTG-BOX",
            price=Decimal("300"),
            valued_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source=ValuationSource.MARKET,
            confidence=ValuationConfidence.HIGH,
        ),
        Valuation(
            asset_id="MTG-BOX",
            price=Decimal("325"),
            valued_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            source=ValuationSource.PLATFORM,
            confidence=ValuationConfidence.MEDIUM,
        ),
    ]
    selected = select_valuation(
        valuations,
        liquidity_tier=LiquidityTier.ILLIQUID,
        as_of=datetime(2026, 2, 10, tzinfo=timezone.utc),
    )
    assert selected is not None
    assert selected.price == Decimal("325")
    assert selected.source == ValuationSource.PLATFORM
