"""Calculated portfolio position model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from .enums import AssetCategory, LiquidityTier


@dataclass(slots=True)
class Position:
    portfolio_id: UUID
    account_id: UUID
    asset_id: str
    asset_name: str
    asset_category: AssetCategory
    quantity: Decimal
    cost_basis: Decimal
    market_value: Decimal
    position_id: UUID = field(default_factory=uuid4)
    currency: str = "USD"
    average_unit_cost: Decimal = Decimal("0")
    unrealized_gain_loss: Decimal = Decimal("0")
    realized_gain_loss: Decimal = Decimal("0")
    portfolio_weight: Decimal = Decimal("0")
    liquidity_tier: LiquidityTier = LiquidityTier.UNKNOWN
    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        decimal_fields = (
            "quantity",
            "cost_basis",
            "market_value",
            "average_unit_cost",
            "unrealized_gain_loss",
            "realized_gain_loss",
            "portfolio_weight",
        )
        for name in decimal_fields:
            setattr(self, name, Decimal(str(getattr(self, name))))

        if self.quantity < 0:
            raise ValueError("Position quantity cannot be negative.")
        if self.cost_basis < 0:
            raise ValueError("Cost basis cannot be negative.")
        if self.market_value < 0:
            raise ValueError("Market value cannot be negative.")
        if self.portfolio_weight < 0 or self.portfolio_weight > 1:
            raise ValueError("Portfolio weight must be between 0 and 1.")
