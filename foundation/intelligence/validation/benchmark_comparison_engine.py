"""Benchmark comparison orchestration across horizons."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .backtest_dataset import BacktestDataset
from .benchmark_metrics import (
    BenchmarkComparisonMetrics,
    calculate_benchmark_metrics,
)


@dataclass(frozen=True, slots=True)
class BenchmarkComparisonReport:
    """Benchmark-relative metrics for every horizon."""

    backtest_id: str
    by_horizon: Mapping[int, BenchmarkComparisonMetrics]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "by_horizon",
            MappingProxyType(dict(self.by_horizon)),
        )


class BenchmarkComparisonEngine:
    """Calculate benchmark-relative metrics for a backtest dataset."""

    def calculate(
        self,
        dataset: BacktestDataset,
    ) -> BenchmarkComparisonReport:
        return BenchmarkComparisonReport(
            backtest_id=dataset.backtest_id,
            by_horizon={
                horizon: calculate_benchmark_metrics(pairs)
                for horizon, pairs in dataset.pairs_by_horizon.items()
            },
        )
