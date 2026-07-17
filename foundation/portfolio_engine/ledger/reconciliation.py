"""Ledger reconciliation calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .ledger_entry import LedgerEntry


@dataclass(slots=True)
class ReconciliationResult:
    expected_count: int
    actual_count: int
    expected_net_amount: Decimal
    actual_net_amount: Decimal
    count_difference: int
    amount_difference: Decimal

    @property
    def is_reconciled(self) -> bool:
        return self.count_difference == 0 and self.amount_difference == 0


def reconcile_entries(
    entries: Iterable[LedgerEntry],
    *,
    expected_count: int,
    expected_net_amount: Decimal,
) -> ReconciliationResult:
    rows = list(entries)
    actual_amount = sum((entry.net_amount for entry in rows), Decimal("0"))
    expected_amount = Decimal(str(expected_net_amount))
    return ReconciliationResult(
        expected_count=expected_count,
        actual_count=len(rows),
        expected_net_amount=expected_amount,
        actual_net_amount=actual_amount,
        count_difference=len(rows) - expected_count,
        amount_difference=actual_amount - expected_amount,
    )
