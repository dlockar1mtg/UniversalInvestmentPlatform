from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from foundation.portfolio_engine.models import (
    AssetCategory,
    LiquidityTier,
)
from foundation.portfolio_engine.positions import ValuedPosition
from foundation.portfolio_engine.snapshots import build_snapshot


def test_snapshot_sums_positions_cash_and_stale_value() -> None:
    portfolio_id = uuid4()
    position = ValuedPosition(
        portfolio_id=portfolio_id,
        account_id=uuid4(),
        asset_id="BTC",
        asset_name="Bitcoin",
        asset_category=AssetCategory.CRYPTO,
        quantity=Decimal("1"),
        average_unit_cost=Decimal("50000"),
        cost_basis=Decimal("50000"),
        latest_price=Decimal("60000"),
        market_value=Decimal("60000"),
        unrealized_gain_loss=Decimal("10000"),
        realized_gain_loss=Decimal("0"),
        portfolio_weight=Decimal("1"),
        currency="USD",
        liquidity_tier=LiquidityTier.DAILY,
        valued_at=datetime.now(timezone.utc),
        valuation_source=None,
        valuation_confidence=None,
        valuation_age_days=0,
        is_stale=True,
        as_of=datetime.now(timezone.utc),
    )
    snapshot = build_snapshot(
        portfolio_id,
        [position],
        cash_balance=Decimal("1000"),
    )
    assert snapshot.total_market_value == Decimal("61000")
    assert snapshot.stale_valuation_value == Decimal("60000")
