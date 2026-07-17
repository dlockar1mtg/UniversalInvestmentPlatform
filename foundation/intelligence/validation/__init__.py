"""Historical validation contracts and utilities."""

from .backtest_configuration import BacktestConfiguration, RebalanceFrequency
from .backtest_dataset import (
    BacktestDataset,
    BacktestDiagnostics,
    PredictionOutcomePair,
)
from .backtest_schedule import generate_prediction_dates
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
from .validation_profile import ValidationProfile
from .validation_result import ValidationResult
from .walk_forward_engine import (
    PredictionFunction,
    WalkForwardBacktestEngine,
    WalkForwardRequest,
)

__all__ = [
    "BacktestConfiguration",
    "BacktestDataset",
    "BacktestDiagnostics",
    "HistoricalObservation",
    "OutcomeRecord",
    "PredictionFunction",
    "PredictionOutcomePair",
    "PredictionRecord",
    "RebalanceFrequency",
    "ValidationProfile",
    "ValidationResult",
    "WalkForwardBacktestEngine",
    "WalkForwardRequest",
    "assert_no_future_observations",
    "build_outcome",
    "calculate_maximum_drawdown",
    "calculate_total_return",
    "generate_prediction_dates",
    "group_observations_by_asset",
    "select_latest_observations",
]
