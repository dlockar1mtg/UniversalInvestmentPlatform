"""Projected allocation calculations after contributions."""

from __future__ import annotations

from decimal import Decimal


def projected_weight(
    current_value: Decimal,
    contribution: Decimal,
    projected_total_value: Decimal,
) -> Decimal:
    total = Decimal(str(projected_total_value))
    if total <= 0:
        return Decimal("0")
    return (Decimal(str(current_value)) + Decimal(str(contribution))) / total


def projected_drift(
    current_value: Decimal,
    contribution: Decimal,
    projected_total_value: Decimal,
    target_weight: Decimal,
) -> Decimal:
    return projected_weight(
        current_value,
        contribution,
        projected_total_value,
    ) - Decimal(str(target_weight))
