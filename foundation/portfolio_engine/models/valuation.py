"""Asset valuation domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from .enums import ValuationConfidence, ValuationSource


@dataclass(slots=True)
class Valuation:
    asset_id: str
    price: Decimal
    valued_at: datetime
    source: ValuationSource
    valuation_id: UUID = field(default_factory=uuid4)
    account_id: UUID | None = None
    currency: str = "USD"
    confidence: ValuationConfidence = ValuationConfidence.UNKNOWN
    source_reference: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.price = Decimal(str(self.price))
        self.currency = self.currency.strip().upper()
        if not self.asset_id.strip():
            raise ValueError("Asset ID is required.")
        if self.price < 0:
            raise ValueError("Valuation price cannot be negative.")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a three-letter code.")
