"""Application service for portfolio performance analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from foundation.portfolio_engine.risk import ValuePoint, build_risk_summary

from .benchmark_comparison import BenchmarkComparison, compare_to_benchmark
from .money_weighted_return import DatedCashFlow, calculate_money_weighted_return
from .return_calculator import annualize_return
from .time_weighted_return import calculate_time_weighted_return
from .performance_repository import PerformanceRepository


@dataclass(slots=True)
class PerformanceSummary:
    period_start: date
    period_end: date
    period_return: Decimal
    time_weighted_return: Decimal
    money_weighted_return: Decimal
    annualized_return: Decimal
    risk_summary: object
    benchmark_comparison: BenchmarkComparison | None


class PerformanceService:
    def __init__(self, repository: PerformanceRepository) -> None:
        self.repository = repository

    def calculate_and_store(
        self,
        *,
        portfolio_id: UUID,
        period_returns: list[Decimal],
        value_points: list[ValuePoint],
        cash_flows: list[DatedCashFlow],
        periods_per_year: int = 12,
        benchmark_returns: list[Decimal] | None = None,
        benchmark_key: str | None = None,
    ) -> tuple[UUID, PerformanceSummary]:
        if not period_returns or not value_points:
            raise ValueError("Performance calculation requires returns and value points.")

        twr = calculate_time_weighted_return(period_returns)
        mwr = calculate_money_weighted_return(cash_flows)
        annualized = annualize_return(
            twr,
            periods=len(period_returns),
            periods_per_year=periods_per_year,
        )
        risk = build_risk_summary(
            period_returns,
            value_points,
            annualized_return=annualized,
            periods_per_year=periods_per_year,
        )
        benchmark = (
            compare_to_benchmark(
                period_returns,
                benchmark_returns,
                periods_per_year=periods_per_year,
            )
            if benchmark_returns is not None
            else None
        )

        summary = PerformanceSummary(
            period_start=value_points[0].date_value,
            period_end=value_points[-1].date_value,
            period_return=twr,
            time_weighted_return=twr,
            money_weighted_return=mwr,
            annualized_return=annualized,
            risk_summary=risk,
            benchmark_comparison=benchmark,
        )

        run_id = self.repository.store_summary(
            portfolio_id=portfolio_id,
            period_start=summary.period_start,
            period_end=summary.period_end,
            period_return=summary.period_return,
            time_weighted_return=summary.time_weighted_return,
            money_weighted_return=summary.money_weighted_return,
            annualized_return=summary.annualized_return,
            risk_summary=summary.risk_summary,
            benchmark_key=benchmark_key,
            benchmark_return=(
                benchmark.benchmark_return if benchmark else None
            ),
            excess_return=(
                benchmark.excess_return if benchmark else None
            ),
        )
        return run_id, summary
