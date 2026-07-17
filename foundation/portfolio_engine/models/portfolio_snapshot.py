"""Point-in-time portfolio snapshot model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(slots=True)
class PortfolioSnapshot:
    portfolio_id: UUID
    total_market_value: Decimal
    total_cost_basis: Decimal
    cash_balance: Decimal
    position_count: int
    snapshot_id: UUID = field(default_factory=uuid4)
    total_unrealized_gain_loss: Decimal = Decimal("0")
    total_realized_gain_loss: Decimal = Decimal("0")
    stale_valuation_value: Decimal = Decimal("0")
    snapshot_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for name in (
            "total_market_value",
            "total_cost_basis",
            "cash_balance",
            "total_unrealized_gain_loss",
            "total_realized_gain_loss",
            "stale_valuation_value",
        ):
            setattr(self, name, Decimal(str(getattr(self, name))))

        if self.total_market_value < 0:
            raise ValueError("Total market value cannot be negative.")
        if self.total_cost_basis < 0:
            raise ValueError("Total cost basis cannot be negative.")
        if self.position_count < 0:
            raise ValueError("Position count cannot be negative.")
