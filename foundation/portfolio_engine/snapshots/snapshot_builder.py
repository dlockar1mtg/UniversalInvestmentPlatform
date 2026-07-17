"""Build point-in-time portfolio snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from foundation.portfolio_engine.models import PortfolioSnapshot
from foundation.portfolio_engine.positions import ValuedPosition


def build_snapshot(
    portfolio_id: UUID,
    positions: list[ValuedPosition],
    *,
    cash_balance: Decimal = Decimal("0"),
    snapshot_at: datetime | None = None,
) -> PortfolioSnapshot:
    timestamp = snapshot_at or datetime.now(timezone.utc)
    return PortfolioSnapshot(
        portfolio_id=portfolio_id,
        total_market_value=sum(
            (position.market_value for position in positions),
            Decimal("0"),
        ) + Decimal(str(cash_balance)),
        total_cost_basis=sum(
            (position.cost_basis for position in positions),
            Decimal("0"),
        ),
        cash_balance=Decimal(str(cash_balance)),
        total_unrealized_gain_loss=sum(
            (position.unrealized_gain_loss for position in positions),
            Decimal("0"),
        ),
        total_realized_gain_loss=sum(
            (position.realized_gain_loss for position in positions),
            Decimal("0"),
        ),
        stale_valuation_value=sum(
            (
                position.market_value
                for position in positions
                if position.is_stale
            ),
            Decimal("0"),
        ),
        position_count=len(positions),
        snapshot_at=timestamp,
    )
