"""Volatility calculations."""

from __future__ import annotations

from decimal import Decimal
from math import sqrt
from typing import Iterable


def annualized_volatility(
    returns: Iterable[Decimal],
    *,
    periods_per_year: int = 12,
) -> Decimal:
    values = [Decimal(str(value)) for value in returns]
    if len(values) < 2:
        return Decimal("0")
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)
    return Decimal(str(sqrt(float(variance) * periods_per_year)))
