"""Historical validation contracts and utilities."""

from .backtest_configuration import BacktestConfiguration, RebalanceFrequency
from .backtest_dataset import (
    BacktestDataset,
    BacktestDiagnostics,
    PredictionOutcomePair,
)
from .backtest_schedule import generate_prediction_dates
from .benchmark_comparison_engine import (
    BenchmarkComparisonEngine,
    BenchmarkComparisonReport,
)
from .benchmark_loader import load_benchmark_registry
from .benchmark_metrics import (
    BenchmarkComparisonMetrics,
    calculate_alpha,
    calculate_benchmark_metrics,
    calculate_beta,
    calculate_capture_ratio,
    calculate_relative_max_drawdown,
)
from .benchmark_registry import BenchmarkDefinition, BenchmarkRegistry
from .calibration_metrics import (
    BucketPerformance,
    CalibrationSummary,
    calculate_calibration_error,
    calculate_calibration_summary,
    performance_by_quantile,
    performance_by_score_band,
)
from .classification_metrics import (
    ClassificationMetrics,
    calculate_classification_metrics,
)
from .cross_asset_adapter import build_asset_class_summary
from .cross_asset_contracts import (
    AssetClassValidationSummary,
    CrossAssetGrade,
    CrossAssetValidationReport,
)
from .cross_asset_engine import CrossAssetValidationEngine
from .cross_asset_grading import grade_asset_class
from .cross_asset_limitations import (
    DEFAULT_LIMITATIONS,
    limitations_for_asset_class,
)
from .historical_observation import HistoricalObservation
from .outcome_alignment import (
    build_outcome,
    calculate_maximum_drawdown,
    calculate_total_return,
)
from .outcome_record import OutcomeRecord
from .point_in_time import (
    assert_no_future_observations,
    group_observations_by_asset,
    select_latest_observations,
)
from .prediction_record import PredictionRecord
from .ranking_metrics import (
    RankCorrelationResult,
    calculate_rank_correlations,
    kendall_rank_correlation,
    spearman_rank_correlation,
)
from .stability_metrics import (
    HorizonStabilitySummary,
    calculate_horizon_stability,
)
from .validation_metrics_engine import (
    HorizonValidationMetrics,
    ValidationMetricsEngine,
    ValidationMetricsReport,
)
from .validation_profile import ValidationProfile
from .validation_result import ValidationResult
from .walk_forward_engine import (
    PredictionFunction,
    WalkForwardBacktestEngine,
    WalkForwardRequest,
)

__all__ = [
    "AssetClassValidationSummary",
    "BacktestConfiguration",
    "BacktestDataset",
    "BacktestDiagnostics",
    "BenchmarkComparisonEngine",
    "BenchmarkComparisonMetrics",
    "BenchmarkComparisonReport",
    "BenchmarkDefinition",
    "BenchmarkRegistry",
    "BucketPerformance",
    "CalibrationSummary",
    "ClassificationMetrics",
    "CrossAssetGrade",
    "CrossAssetValidationEngine",
    "CrossAssetValidationReport",
    "DEFAULT_LIMITATIONS",
    "HistoricalObservation",
    "HorizonStabilitySummary",
    "HorizonValidationMetrics",
    "OutcomeRecord",
    "PredictionFunction",
    "PredictionOutcomePair",
    "PredictionRecord",
    "RankCorrelationResult",
    "RebalanceFrequency",
    "ValidationMetricsEngine",
    "ValidationMetricsReport",
    "ValidationProfile",
    "ValidationResult",
    "WalkForwardBacktestEngine",
    "WalkForwardRequest",
    "assert_no_future_observations",
    "build_asset_class_summary",
    "build_outcome",
    "calculate_alpha",
    "calculate_benchmark_metrics",
    "calculate_beta",
    "calculate_calibration_error",
    "calculate_calibration_summary",
    "calculate_capture_ratio",
    "calculate_classification_metrics",
    "calculate_horizon_stability",
    "calculate_maximum_drawdown",
    "calculate_rank_correlations",
    "calculate_relative_max_drawdown",
    "calculate_total_return",
    "generate_prediction_dates",
    "grade_asset_class",
    "group_observations_by_asset",
    "kendall_rank_correlation",
    "limitations_for_asset_class",
    "load_benchmark_registry",
    "performance_by_quantile",
    "performance_by_score_band",
    "select_latest_observations",
    "spearman_rank_correlation",
]
