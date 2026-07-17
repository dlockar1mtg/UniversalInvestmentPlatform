"""Orchestrate ranking, classification, calibration, and stability metrics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .backtest_dataset import BacktestDataset
from .calibration_metrics import CalibrationSummary, calculate_calibration_summary
from .classification_metrics import (
    ClassificationMetrics,
    calculate_classification_metrics,
)
from .ranking_metrics import RankCorrelationResult, calculate_rank_correlations
from .stability_metrics import (
    HorizonStabilitySummary,
    calculate_horizon_stability,
)


@dataclass(frozen=True, slots=True)
class HorizonValidationMetrics:
    """All metrics calculated for one forward horizon."""

    horizon_days: int
    rank_correlation: RankCorrelationResult
    classification: ClassificationMetrics
    calibration: CalibrationSummary


@dataclass(frozen=True, slots=True)
class ValidationMetricsReport:
    """Complete metrics report for a backtest dataset."""

    backtest_id: str
    horizons: Mapping[int, HorizonValidationMetrics]
    stability: HorizonStabilitySummary

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "horizons",
            MappingProxyType(dict(self.horizons)),
        )


class ValidationMetricsEngine:
    """Calculate validation metrics for every horizon in a backtest dataset."""

    def calculate(
        self,
        dataset: BacktestDataset,
        *,
        positive_score_threshold: Decimal = Decimal("70"),
        positive_return_threshold: Decimal = Decimal("0"),
        quantile_count: int = 5,
    ) -> ValidationMetricsReport:
        horizon_results = {}
        for horizon, pairs in dataset.pairs_by_horizon.items():
            horizon_results[horizon] = HorizonValidationMetrics(
                horizon_days=horizon,
                rank_correlation=calculate_rank_correlations(pairs),
                classification=calculate_classification_metrics(
                    pairs,
                    positive_score_threshold=positive_score_threshold,
                    positive_return_threshold=positive_return_threshold,
                ),
                calibration=calculate_calibration_summary(
                    pairs,
                    quantile_count=quantile_count,
                ),
            )

        return ValidationMetricsReport(
            backtest_id=dataset.backtest_id,
            horizons=horizon_results,
            stability=calculate_horizon_stability(dataset),
        )
