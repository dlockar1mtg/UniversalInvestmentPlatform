"""Combine derived positions with selected valuations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from foundation.portfolio_engine.models import (
    AssetCategory,
    LiquidityTier,
    ValuationConfidence,
    ValuationSource,
)
from foundation.portfolio_engine.valuations import SelectedValuation

from .position_builder import DerivedPosition


@dataclass(slots=True)
class ValuedPosition:
    portfolio_id: UUID
    account_id: UUID
    asset_id: str
    asset_name: str
    asset_category: AssetCategory
    quantity: Decimal
    average_unit_cost: Decimal
    cost_basis: Decimal
    latest_price: Decimal
    market_value: Decimal
    unrealized_gain_loss: Decimal
    realized_gain_loss: Decimal
    portfolio_weight: Decimal
    currency: str
    liquidity_tier: LiquidityTier
    valued_at: datetime | None
    valuation_source: ValuationSource | None
    valuation_confidence: ValuationConfidence | None
    valuation_age_days: int | None
    is_stale: bool
    as_of: datetime
    position_id: UUID = field(default_factory=uuid4)


def value_positions(
    positions: list[DerivedPosition],
    valuations: dict[tuple[str, UUID | None], SelectedValuation],
) -> list[ValuedPosition]:
    preliminary: list[ValuedPosition] = []
    total_market_value = Decimal("0")

    for position in positions:
        selected = valuations.get((position.asset_id, position.account_id))
        if selected is None:
            selected = valuations.get((position.asset_id, None))

        price = selected.price if selected else Decimal("0")
        market_value = position.quantity * price
        total_market_value += market_value

        preliminary.append(
            ValuedPosition(
                portfolio_id=position.portfolio_id,
                account_id=position.account_id,
                asset_id=position.asset_id,
                asset_name=position.asset_name,
                asset_category=position.asset_category,
                quantity=position.quantity,
                average_unit_cost=position.average_unit_cost,
                cost_basis=position.cost_basis,
                latest_price=price,
                market_value=market_value,
                unrealized_gain_loss=market_value - position.cost_basis,
                realized_gain_loss=position.realized_gain_loss,
                portfolio_weight=Decimal("0"),
                currency=position.currency,
                liquidity_tier=position.liquidity_tier,
                valued_at=selected.valued_at if selected else None,
                valuation_source=selected.source if selected else None,
                valuation_confidence=selected.confidence if selected else None,
                valuation_age_days=selected.age_days if selected else None,
                is_stale=True if selected is None else selected.is_stale,
                as_of=position.as_of,
            )
        )

    if total_market_value > 0:
        for position in preliminary:
            position.portfolio_weight = position.market_value / total_market_value

    return preliminary
