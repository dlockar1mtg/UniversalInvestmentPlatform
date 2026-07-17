from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from foundation.portfolio_engine.allocation import (
    AllocationStatus,
    calculate_allocation,
    load_allocation_targets,
)
from foundation.portfolio_engine.models import AssetCategory, LiquidityTier
from foundation.portfolio_engine.positions import ValuedPosition


ROOT = Path(__file__).resolve().parents[2]


def _position(portfolio_id, category, value, asset_id):
    return ValuedPosition(
        portfolio_id=portfolio_id,
        account_id=uuid4(),
        asset_id=asset_id,
        asset_name=asset_id,
        asset_category=category,
        quantity=Decimal("1"),
        average_unit_cost=value,
        cost_basis=value,
        latest_price=value,
        market_value=value,
        unrealized_gain_loss=Decimal("0"),
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


def test_allocation_matches_target_weights() -> None:
    portfolio_id = uuid4()
    positions = [
        _position(portfolio_id, AssetCategory.CRYPTO, Decimal("33000"), "BTC"),
        _position(portfolio_id, AssetCategory.MTG, Decimal("20000"), "MTG"),
        _position(portfolio_id, AssetCategory.METALS, Decimal("10000"), "GLD"),
        _position(portfolio_id, AssetCategory.ACORNS, Decimal("10000"), "ACORNS"),
        _position(portfolio_id, AssetCategory.STOCKS_ETFS, Decimal("27000"), "VOO"),
    ]
    targets = load_allocation_targets(
        ROOT / "config/portfolios/allocation_targets.yaml"
    )
    summary = calculate_allocation(positions, targets)
    assert summary.invested_value == Decimal("100000")
    assert all(row.status == AllocationStatus.WITHIN_BAND for row in summary.rows)
