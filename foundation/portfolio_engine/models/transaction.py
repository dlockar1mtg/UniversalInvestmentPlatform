"""Universal portfolio transaction model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from .enums import AssetCategory, TransactionType


@dataclass(slots=True)
class Transaction:
    portfolio_id: UUID
    account_id: UUID
    transaction_type: TransactionType
    transaction_at: datetime
    amount: Decimal
    currency: str = "USD"
    transaction_id: UUID = field(default_factory=uuid4)
    asset_id: str | None = None
    asset_name: str | None = None
    asset_category: AssetCategory | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    fees: Decimal = Decimal("0")
    source_platform: str | None = None
    source_record_id: str | None = None
    notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.amount = Decimal(str(self.amount))
        self.fees = Decimal(str(self.fees))
        self.quantity = None if self.quantity is None else Decimal(str(self.quantity))
        self.unit_price = None if self.unit_price is None else Decimal(str(self.unit_price))
        self.currency = self.currency.strip().upper()

        if len(self.currency) != 3:
            raise ValueError("Currency must be a three-letter code.")
        if self.amount < 0:
            raise ValueError("Transaction amount cannot be negative.")
        if self.fees < 0:
            raise ValueError("Transaction fees cannot be negative.")
        if self.quantity is not None and self.quantity < 0:
            raise ValueError("Transaction quantity cannot be negative.")
        if self.unit_price is not None and self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")
        if self.transaction_type in {TransactionType.BUY, TransactionType.SELL}:
            if not self.asset_id:
                raise ValueError("Buy and sell transactions require asset_id.")
            if self.quantity is None or self.quantity <= 0:
                raise ValueError("Buy and sell transactions require positive quantity.")
