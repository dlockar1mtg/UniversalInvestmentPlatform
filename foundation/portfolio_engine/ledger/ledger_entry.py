"""Append-only Universal Portfolio Ledger entry."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from foundation.portfolio_engine.models import AssetCategory, TransactionType

from .audit import calculate_audit_hash


class LedgerEntryStatus(StrEnum):
    POSTED = "posted"
    REVERSED = "reversed"
    REJECTED = "rejected"


@dataclass(slots=True)
class LedgerEntry:
    portfolio_id: UUID
    account_id: UUID
    transaction_type: TransactionType
    effective_at: datetime
    gross_amount: Decimal
    net_amount: Decimal
    currency: str = "USD"
    ledger_entry_id: UUID = field(default_factory=uuid4)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    asset_id: str | None = None
    asset_name: str | None = None
    asset_category: AssetCategory | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    fees: Decimal = Decimal("0")
    source_platform: str | None = None
    source_file: str | None = None
    source_record_id: str | None = None
    import_run_id: UUID | None = None
    reversal_of_entry_id: UUID | None = None
    entry_status: LedgerEntryStatus = LedgerEntryStatus.POSTED
    metadata: dict[str, Any] = field(default_factory=dict)
    audit_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("gross_amount", "net_amount", "fees"):
            setattr(self, name, Decimal(str(getattr(self, name))))
        self.quantity = None if self.quantity is None else Decimal(str(self.quantity))
        self.unit_price = None if self.unit_price is None else Decimal(str(self.unit_price))
        self.currency = self.currency.strip().upper()

        if len(self.currency) != 3:
            raise ValueError("Currency must be a three-letter code.")
        if self.gross_amount < 0:
            raise ValueError("Gross amount cannot be negative.")
        if self.fees < 0:
            raise ValueError("Fees cannot be negative.")
        if self.quantity is not None and self.quantity < 0:
            raise ValueError("Quantity cannot be negative.")
        if self.unit_price is not None and self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")
        if self.transaction_type in {TransactionType.BUY, TransactionType.SELL}:
            if not self.asset_id:
                raise ValueError("Buy and sell entries require asset_id.")
            if self.quantity is None or self.quantity <= 0:
                raise ValueError("Buy and sell entries require positive quantity.")
        if self.transaction_type in {
            TransactionType.TRANSFER_IN,
            TransactionType.TRANSFER_OUT,
        } and not self.account_id:
            raise ValueError("Transfer entries require account_id.")

        expected_net = self.expected_net_amount()
        if self.net_amount != expected_net:
            raise ValueError(
                f"Net amount {self.net_amount} does not match expected {expected_net}."
            )

        self.audit_hash = calculate_audit_hash(self)

    def expected_net_amount(self) -> Decimal:
        if self.transaction_type in {
            TransactionType.BUY,
            TransactionType.WITHDRAWAL,
            TransactionType.FEE,
            TransactionType.TRANSFER_OUT,
        }:
            return -(self.gross_amount + self.fees)
        if self.transaction_type in {
            TransactionType.SELL,
            TransactionType.DEPOSIT,
            TransactionType.DIVIDEND,
            TransactionType.DISTRIBUTION,
            TransactionType.INTEREST,
            TransactionType.TRANSFER_IN,
        }:
            return self.gross_amount - self.fees
        return self.net_amount

    @property
    def metadata_json(self) -> str:
        return json.dumps(self.metadata, sort_keys=True, separators=(",", ":"))
