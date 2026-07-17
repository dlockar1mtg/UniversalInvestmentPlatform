"""Investment account domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .enums import AccountType


@dataclass(slots=True)
class Account:
    portfolio_id: UUID
    name: str
    institution: str
    account_type: AccountType
    account_id: UUID = field(default_factory=uuid4)
    external_account_id: str | None = None
    currency: str = "USD"
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.institution = self.institution.strip()
        self.currency = self.currency.strip().upper()

        if not self.name:
            raise ValueError("Account name is required.")
        if not self.institution:
            raise ValueError("Institution is required.")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a three-letter code.")
