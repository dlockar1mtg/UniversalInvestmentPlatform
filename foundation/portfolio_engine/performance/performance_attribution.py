"""Approximate beginning-weight performance attribution."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(slots=True)
class AttributionInput:
    key: str
    beginning_weight: Decimal
    period_return: Decimal


@dataclass(slots=True)
class AttributionResult:
    key: str
    beginning_weight: Decimal
    period_return: Decimal
    contribution_to_return: Decimal
    contribution_share: Decimal


def calculate_attribution(
    rows: Iterable[AttributionInput],
) -> list[AttributionResult]:
    inputs = list(rows)
    contributions = [
        item.beginning_weight * item.period_return
        for item in inputs
    ]
    total = sum(contributions, Decimal("0"))

    return [
        AttributionResult(
            key=item.key,
            beginning_weight=item.beginning_weight,
            period_return=item.period_return,
            contribution_to_return=contribution,
            contribution_share=(
                Decimal("0") if total == 0 else contribution / total
            ),
        )
        for item, contribution in zip(inputs, contributions)
    ]
