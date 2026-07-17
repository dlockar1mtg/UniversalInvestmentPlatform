"""Downside-risk calculations."""

from __future__ import annotations

from decimal import Decimal
from math import sqrt
from typing import Iterable


def downside_deviation(
    returns: Iterable[Decimal],
    *,
    minimum_acceptable_return: Decimal = Decimal("0"),
    periods_per_year: int = 12,
) -> Decimal:
    values = [Decimal(str(value)) for value in returns]
    if not values:
        return Decimal("0")

    target = Decimal(str(minimum_acceptable_return))
    downside = [min(value - target, Decimal("0")) for value in values]
    semivariance = sum(value * value for value in downside) / Decimal(len(values))
    return Decimal(str(sqrt(float(semivariance) * periods_per_year)))
