"""Portfolio performance analytics."""

from .benchmark_comparison import BenchmarkComparison, compare_to_benchmark
from .money_weighted_return import DatedCashFlow, calculate_money_weighted_return
from .performance_attribution import (
    AttributionInput,
    AttributionResult,
    calculate_attribution,
)
from .performance_repository import PerformanceRepository
from .performance_service import PerformanceService, PerformanceSummary
from .return_calculator import PeriodReturn, annualize_return, calculate_period_return
from .rolling_returns import ReturnPoint, RollingReturn, calculate_rolling_returns
from .time_weighted_return import calculate_time_weighted_return

__all__ = [
    "AttributionInput",
    "AttributionResult",
    "BenchmarkComparison",
    "DatedCashFlow",
    "PerformanceRepository",
    "PerformanceService",
    "PerformanceSummary",
    "PeriodReturn",
    "ReturnPoint",
    "RollingReturn",
    "annualize_return",
    "calculate_attribution",
    "calculate_money_weighted_return",
    "calculate_period_return",
    "calculate_rolling_returns",
    "calculate_time_weighted_return",
    "compare_to_benchmark",
]
