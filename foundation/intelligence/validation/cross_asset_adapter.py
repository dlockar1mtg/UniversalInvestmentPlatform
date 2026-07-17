"""Adapt existing validation reports into cross-asset summaries."""

from __future__ import annotations

from decimal import Decimal

from .benchmark_comparison_engine import BenchmarkComparisonReport
from .cross_asset_contracts import AssetClassValidationSummary
from .validation_metrics_engine import ValidationMetricsReport


def build_asset_class_summary(
    *,
    asset_class: str,
    model_id: str,
    model_version: str,
    horizon_days: int,
    observation_count: int,
    asset_count: int,
    coverage_ratio: Decimal,
    metrics_report: ValidationMetricsReport,
    benchmark_report: BenchmarkComparisonReport,
    limitations: tuple[str, ...] = (),
) -> AssetClassValidationSummary:
    """Combine horizon metrics and benchmark metrics into one comparable summary."""
    horizon_metrics = metrics_report.horizons.get(horizon_days)
    benchmark_metrics = benchmark_report.by_horizon.get(horizon_days)
    if horizon_metrics is None:
        raise KeyError(f"Missing validation metrics for horizon {horizon_days}.")
    if benchmark_metrics is None:
        raise KeyError(f"Missing benchmark metrics for horizon {horizon_days}.")

    return AssetClassValidationSummary(
        asset_class=asset_class,
        model_id=model_id,
        model_version=model_version,
        horizon_days=horizon_days,
        observation_count=observation_count,
        asset_count=asset_count,
        coverage_ratio=coverage_ratio,
        spearman=horizon_metrics.rank_correlation.spearman,
        kendall=horizon_metrics.rank_correlation.kendall,
        hit_rate=horizon_metrics.classification.hit_rate,
        top_bottom_spread=horizon_metrics.calibration.top_bottom_spread,
        mean_excess_return=benchmark_metrics.mean_excess_return,
        information_ratio=benchmark_metrics.information_ratio,
        benchmark_win_rate=benchmark_metrics.benchmark_win_rate,
        calibration_error=horizon_metrics.calibration.calibration_error,
        limitations=limitations,
    )
