"""Apply category-level purchase constraints."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(slots=True)
class PurchaseConstraintResult:
    requested_amount: Decimal
    executable_amount: Decimal
    retained_amount: Decimal
    is_executable: bool
    reason: str


def apply_purchase_constraints(
    requested_amount: Decimal,
    *,
    minimum_purchase_amount: Decimal,
    allow_fractional: bool,
    purchase_increment: Decimal | None = None,
) -> PurchaseConstraintResult:
    requested = Decimal(str(requested_amount))
    minimum = Decimal(str(minimum_purchase_amount))
    increment = None if purchase_increment is None else Decimal(str(purchase_increment))

    if requested <= 0:
        return PurchaseConstraintResult(
            requested_amount=requested,
            executable_amount=Decimal("0"),
            retained_amount=max(requested, Decimal("0")),
            is_executable=False,
            reason="no_requested_amount",
        )

    if requested < minimum:
        return PurchaseConstraintResult(
            requested_amount=requested,
            executable_amount=Decimal("0"),
            retained_amount=requested,
            is_executable=False,
            reason="below_minimum_purchase",
        )

    if allow_fractional:
        return PurchaseConstraintResult(
            requested_amount=requested,
            executable_amount=requested,
            retained_amount=Decimal("0"),
            is_executable=True,
            reason="fractional_purchase_allowed",
        )

    effective_increment = increment or minimum
    if effective_increment <= 0:
        raise ValueError("Non-fractional purchases require a positive increment.")

    units = (requested / effective_increment).to_integral_value(rounding=ROUND_DOWN)
    executable = units * effective_increment
    retained = requested - executable

    if executable < minimum:
        return PurchaseConstraintResult(
            requested_amount=requested,
            executable_amount=Decimal("0"),
            retained_amount=requested,
            is_executable=False,
            reason="no_whole_purchase_available",
        )

    return PurchaseConstraintResult(
        requested_amount=requested,
        executable_amount=executable,
        retained_amount=retained,
        is_executable=True,
        reason="whole_purchase_increment_applied",
    )
