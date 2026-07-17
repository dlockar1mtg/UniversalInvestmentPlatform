from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from foundation.portfolio_engine.allocation import classify_position
from foundation.portfolio_engine.models import AssetCategory, LiquidityTier
from foundation.portfolio_engine.positions import ValuedPosition


def test_gld_is_classified_as_metals() -> None:
    position = ValuedPosition(
        portfolio_id=uuid4(),
        account_id=uuid4(),
        asset_id="GLD",
        asset_name="SPDR Gold Shares",
        asset_category=AssetCategory.STOCKS_ETFS,
        quantity=Decimal("1"),
        average_unit_cost=Decimal("200"),
        cost_basis=Decimal("200"),
        latest_price=Decimal("210"),
        market_value=Decimal("210"),
        unrealized_gain_loss=Decimal("10"),
        realized_gain_loss=Decimal("0"),
        portfolio_weight=Decimal("0"),
        currency="USD",
        liquidity_tier=LiquidityTier.DAILY,
        valued_at=datetime.now(timezone.utc),
        valuation_source=None,
        valuation_confidence=None,
        valuation_age_days=0,
        is_stale=False,
        as_of=datetime.now(timezone.utc),
    )
    classified = classify_position(position)
    assert classified.asset_category == AssetCategory.METALS
