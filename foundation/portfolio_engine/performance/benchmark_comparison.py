"""Portfolio versus benchmark comparison."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
from typing import Iterable


@dataclass(slots=True)
class BenchmarkComparison:
    portfolio_return: Decimal
    benchmark_return: Decimal
    excess_return: Decimal
    tracking_error: Decimal
    information_ratio: Decimal


def compare_to_benchmark(
    portfolio_returns: Iterable[Decimal],
    benchmark_returns: Iterable[Decimal],
    *,
    periods_per_year: int = 12,
) -> BenchmarkComparison:
    portfolio = [Decimal(str(value)) for value in portfolio_returns]
    benchmark = [Decimal(str(value)) for value in benchmark_returns]
    if len(portfolio) != len(benchmark) or not portfolio:
        raise ValueError("Portfolio and benchmark series must be equal, nonzero length.")

    active = [p - b for p, b in zip(portfolio, benchmark)]
    average_active = sum(active, Decimal("0")) / Decimal(len(active))

    if len(active) < 2:
        tracking_error = Decimal("0")
    else:
        variance = sum(
            (value - average_active) ** 2 for value in active
        ) / Decimal(len(active) - 1)
        tracking_error = Decimal(str(sqrt(float(variance) * periods_per_year)))

    portfolio_total = Decimal("1")
    benchmark_total = Decimal("1")
    for value in portfolio:
        portfolio_total *= Decimal("1") + value
    for value in benchmark:
        benchmark_total *= Decimal("1") + value

    information_ratio = (
        Decimal("0")
        if tracking_error == 0
        else average_active * Decimal(periods_per_year) / tracking_error
    )

    return BenchmarkComparison(
        portfolio_return=portfolio_total - Decimal("1"),
        benchmark_return=benchmark_total - Decimal("1"),
        excess_return=(portfolio_total - benchmark_total),
        tracking_error=tracking_error,
        information_ratio=information_ratio,
    )
