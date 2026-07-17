"""Walk-forward backtesting orchestration engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Iterable

from .backtest_configuration import BacktestConfiguration
from .backtest_dataset import (
    BacktestDataset,
    BacktestDiagnostics,
    PredictionOutcomePair,
)
from .backtest_schedule import generate_prediction_dates
from .historical_observation import HistoricalObservation
from .outcome_alignment import build_outcome
from .point_in_time import select_latest_observations
from .prediction_record import PredictionRecord


PredictionFunction = Callable[
    [HistoricalObservation, date, BacktestConfiguration],
    PredictionRecord | None,
]


@dataclass(frozen=True, slots=True)
class WalkForwardRequest:
    configuration: BacktestConfiguration
    observations: tuple[HistoricalObservation, ...]


class WalkForwardBacktestEngine:
    """Generate point-in-time predictions and forward outcomes."""

    def run(
        self,
        request: WalkForwardRequest,
        prediction_function: PredictionFunction,
    ) -> BacktestDataset:
        config = request.configuration
        observations = tuple(request.observations)
        prediction_dates = generate_prediction_dates(config)

        predictions: list[PredictionRecord] = []
        outcomes = []
        pairs_by_horizon: dict[int, list[PredictionOutcomePair]] = {
            horizon: [] for horizon in config.horizons_days
        }

        missing_observations = 0
        missing_outcomes = 0
        filtered_predictions = 0
        warnings: list[str] = []

        for prediction_date in prediction_dates:
            latest = select_latest_observations(observations, prediction_date)
            if not latest:
                missing_observations += 1
                warnings.append(
                    f"No observations available on {prediction_date.isoformat()}."
                )
                continue

            for observation in latest.values():
                prediction = prediction_function(
                    observation,
                    prediction_date,
                    config,
                )
                if prediction is None:
                    filtered_predictions += 1
                    continue
                if prediction.prediction_date != prediction_date:
                    raise ValueError(
                        "Prediction function returned an unexpected prediction_date."
                    )
                if prediction.asset_id != observation.asset_id:
                    raise ValueError(
                        "Prediction function returned an unexpected asset_id."
                    )
                if prediction.final_score < config.minimum_score:
                    filtered_predictions += 1
                    continue
                if prediction.confidence_score < config.minimum_confidence:
                    filtered_predictions += 1
                    continue
                if prediction.coverage_ratio < config.minimum_coverage:
                    filtered_predictions += 1
                    continue

                predictions.append(prediction)

                for horizon in config.horizons_days:
                    outcome = build_outcome(
                        prediction,
                        horizon,
                        observations,
                    )
                    if outcome is None:
                        missing_outcomes += 1
                        continue
                    outcomes.append(outcome)
                    pairs_by_horizon[horizon].append(
                        PredictionOutcomePair(
                            prediction=prediction,
                            outcome=outcome,
                        )
                    )

        diagnostics = BacktestDiagnostics(
            prediction_dates_generated=len(prediction_dates),
            predictions_generated=len(predictions),
            outcomes_generated=len(outcomes),
            missing_observations=missing_observations,
            missing_outcomes=missing_outcomes,
            filtered_predictions=filtered_predictions,
            warnings=tuple(dict.fromkeys(warnings)),
        )

        return BacktestDataset(
            backtest_id=config.backtest_id,
            predictions=tuple(predictions),
            outcomes=tuple(outcomes),
            pairs_by_horizon={
                horizon: tuple(pairs)
                for horizon, pairs in pairs_by_horizon.items()
            },
            diagnostics=diagnostics,
        )
