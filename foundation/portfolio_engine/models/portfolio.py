"""Portfolio domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from .enums import PortfolioStatus


@dataclass(slots=True)
class Portfolio:
    name: str
    base_currency: str = "USD"
    monthly_contribution: Decimal = Decimal("0")
    status: PortfolioStatus = PortfolioStatus.ACTIVE
    portfolio_id: UUID = field(default_factory=uuid4)
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.base_currency = self.base_currency.strip().upper()
        self.monthly_contribution = Decimal(str(self.monthly_contribution))

        if not self.name:
            raise ValueError("Portfolio name is required.")
        if len(self.base_currency) != 3:
            raise ValueError("Base currency must be a three-letter code.")
        if self.monthly_contribution < 0:
            raise ValueError("Monthly contribution cannot be negative.")
