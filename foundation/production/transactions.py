"""Append-only user transaction model for UIP application state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import re
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4


_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    TRANSFER = "TRANSFER"
    GIFT = "GIFT"
    ADJUSTMENT = "ADJUSTMENT"


@dataclass(frozen=True)
class InvestmentTransaction:
    transaction_id: str
    transaction_type: TransactionType
    domain_id: str
    asset_id: str
    occurred_at: datetime
    quantity: Decimal
    price_per_unit: Decimal | None
    fees: Decimal
    currency: str
    account_id: str
    destination_account_id: str | None
    venue: str
    external_reference: str
    notes: str
    recorded_at: datetime
    recorded_by: str
    corrects_transaction_id: str | None
    correction_reason: str | None
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.transaction_id.strip():
            raise ValueError("transaction_id is required")
        if not _SLUG.fullmatch(self.domain_id):
            raise ValueError("domain_id must be a lowercase application-state slug")
        if not self.asset_id.strip():
            raise ValueError("asset_id is required")
        if self.occurred_at.tzinfo is None or self.recorded_at.tzinfo is None:
            raise ValueError("transaction timestamps must be timezone-aware")
        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")
        if self.price_per_unit is not None and self.price_per_unit < 0:
            raise ValueError("price_per_unit must not be negative")
        if self.fees < 0:
            raise ValueError("fees must not be negative")
        if not self.currency.strip() or len(self.currency.strip()) != 3:
            raise ValueError("currency must be a three-letter code")
        if not self.account_id.strip():
            raise ValueError("account_id is required")
        if self.transaction_type is TransactionType.TRANSFER:
            if not self.destination_account_id or not self.destination_account_id.strip():
                raise ValueError("TRANSFER requires destination_account_id")
            if self.destination_account_id == self.account_id:
                raise ValueError("TRANSFER source and destination accounts must differ")
        elif self.destination_account_id is not None:
            raise ValueError("destination_account_id is only valid for TRANSFER")
        if self.corrects_transaction_id is None and self.correction_reason is not None:
            raise ValueError("correction_reason requires corrects_transaction_id")
        if self.corrects_transaction_id is not None:
            if self.corrects_transaction_id == self.transaction_id:
                raise ValueError("a transaction cannot correct itself")
            if not self.correction_reason or not self.correction_reason.strip():
                raise ValueError("correction_reason is required for a correction")
        if not self.recorded_by.strip():
            raise ValueError("recorded_by is required")
        object.__setattr__(self, "currency", self.currency.upper())
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def document(self) -> Mapping[str, object]:
        return MappingProxyType({
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type.value,
            "domain_id": self.domain_id,
            "asset_id": self.asset_id,
            "occurred_at": self.occurred_at.isoformat(),
            "quantity": str(self.quantity),
            "price_per_unit": None if self.price_per_unit is None else str(self.price_per_unit),
            "fees": str(self.fees),
            "currency": self.currency,
            "account_id": self.account_id,
            "destination_account_id": self.destination_account_id,
            "venue": self.venue,
            "external_reference": self.external_reference,
            "notes": self.notes,
            "recorded_at": self.recorded_at.isoformat(),
            "recorded_by": self.recorded_by,
            "corrects_transaction_id": self.corrects_transaction_id,
            "correction_reason": self.correction_reason,
            "metadata": dict(self.metadata),
        })


def create_transaction(
    *,
    transaction_type: str | TransactionType,
    domain_id: str,
    asset_id: str,
    occurred_at: datetime,
    quantity: Decimal | str | int | float,
    price_per_unit: Decimal | str | int | float | None,
    fees: Decimal | str | int | float = Decimal("0"),
    currency: str = "USD",
    account_id: str,
    destination_account_id: str | None = None,
    venue: str = "",
    external_reference: str = "",
    notes: str = "",
    recorded_by: str,
    corrects_transaction_id: str | None = None,
    correction_reason: str | None = None,
    metadata: Mapping[str, object] | None = None,
    transaction_id: str | None = None,
    recorded_at: datetime | None = None,
) -> InvestmentTransaction:
    kind = transaction_type if isinstance(transaction_type, TransactionType) else TransactionType(str(transaction_type).upper())
    return InvestmentTransaction(
        transaction_id=transaction_id or str(uuid4()),
        transaction_type=kind,
        domain_id=domain_id.strip().lower(),
        asset_id=asset_id.strip(),
        occurred_at=occurred_at,
        quantity=Decimal(str(quantity)),
        price_per_unit=None if price_per_unit is None else Decimal(str(price_per_unit)),
        fees=Decimal(str(fees)),
        currency=currency.strip().upper(),
        account_id=account_id.strip(),
        destination_account_id=None if destination_account_id is None else destination_account_id.strip(),
        venue=venue.strip(),
        external_reference=external_reference.strip(),
        notes=notes.strip(),
        recorded_at=recorded_at or datetime.now(timezone.utc),
        recorded_by=recorded_by.strip(),
        corrects_transaction_id=corrects_transaction_id,
        correction_reason=None if correction_reason is None else correction_reason.strip(),
        metadata=metadata or {},
    )
