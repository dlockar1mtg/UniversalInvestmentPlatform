"""Core portfolio return calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class PeriodReturn:
    beginning_value: Decimal
    ending_value: Decimal
    net_external_cash_flow: Decimal
    return_value: Decimal


def calculate_period_return(
    *,
    beginning_value: Decimal,
    ending_value: Decimal,
    net_external_cash_flow: Decimal = Decimal("0"),
) -> PeriodReturn:
    beginning = Decimal(str(beginning_value))
    ending = Decimal(str(ending_value))
    flow = Decimal(str(net_external_cash_flow))

    if beginning <= 0:
        raise ValueError("Beginning value must be positive.")

    result = (ending - beginning - flow) / beginning
    return PeriodReturn(
        beginning_value=beginning,
        ending_value=ending,
        net_external_cash_flow=flow,
        return_value=result,
    )


def annualize_return(total_return: Decimal, periods: int, periods_per_year: int) -> Decimal:
    total = Decimal(str(total_return))
    if periods <= 0 or periods_per_year <= 0:
        raise ValueError("Periods and periods_per_year must be positive.")
    return (Decimal("1") + total) ** (
        Decimal(periods_per_year) / Decimal(periods)
    ) - Decimal("1")
