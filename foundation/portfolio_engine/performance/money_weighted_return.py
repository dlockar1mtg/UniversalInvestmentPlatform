"""Money-weighted return using dated cash flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable


@dataclass(slots=True)
class DatedCashFlow:
    date_value: date
    amount: Decimal


def _to_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def _xnpv(rate: float, cash_flows: list[DatedCashFlow]) -> float:
    first = cash_flows[0].date_value
    return sum(
        float(flow.amount)
        / ((1.0 + rate) ** ((_to_date(flow.date_value) - first).days / 365.0))
        for flow in cash_flows
    )


def calculate_money_weighted_return(
    cash_flows: Iterable[DatedCashFlow],
    *,
    guess: float = 0.10,
    tolerance: float = 1e-9,
    max_iterations: int = 200,
) -> Decimal:
    flows = sorted(list(cash_flows), key=lambda item: item.date_value)
    if len(flows) < 2:
        raise ValueError("At least two dated cash flows are required.")
    if not any(flow.amount < 0 for flow in flows):
        raise ValueError("At least one negative cash flow is required.")
    if not any(flow.amount > 0 for flow in flows):
        raise ValueError("At least one positive cash flow is required.")

    low, high = -0.9999, max(guess, 1.0)
    f_low = _xnpv(low, flows)
    f_high = _xnpv(high, flows)

    expansions = 0
    while f_low * f_high > 0 and expansions < 50:
        high *= 2
        f_high = _xnpv(high, flows)
        expansions += 1

    if f_low * f_high > 0:
        raise ValueError("Unable to bracket a money-weighted return solution.")

    for _ in range(max_iterations):
        mid = (low + high) / 2
        f_mid = _xnpv(mid, flows)
        if abs(f_mid) < tolerance:
            return Decimal(str(mid))
        if f_low * f_mid <= 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid

    return Decimal(str((low + high) / 2))
