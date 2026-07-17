"""Time-weighted return calculations."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable


def calculate_time_weighted_return(
    subperiod_returns: Iterable[Decimal],
) -> Decimal:
    growth = Decimal("1")
    count = 0
    for value in subperiod_returns:
        growth *= Decimal("1") + Decimal(str(value))
        count += 1
    if count == 0:
        return Decimal("0")
    return growth - Decimal("1")
