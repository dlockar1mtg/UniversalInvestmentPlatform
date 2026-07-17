"""Cash balance derivation from ledger entries."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from foundation.portfolio_engine.ledger import LedgerEntry


def calculate_cash_balances(
    entries: Iterable[LedgerEntry],
) -> dict[tuple[UUID, str], Decimal]:
    balances: dict[tuple[UUID, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for entry in entries:
        if entry.entry_status.value != "posted":
            continue
        balances[(entry.account_id, entry.currency)] += entry.net_amount
    return dict(balances)
