"""Walk-forward backtest dataset contracts."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .outcome_record import OutcomeRecord
from .prediction_record import PredictionRecord


@dataclass(frozen=True, slots=True)
class PredictionOutcomePair:
    """One prediction aligned to one realized horizon outcome."""

    prediction: PredictionRecord
    outcome: OutcomeRecord

    def __post_init__(self) -> None:
        if self.prediction.asset_id != self.outcome.asset_id:
            raise ValueError("Prediction and outcome asset_id values must match.")
        if self.prediction.prediction_date != self.outcome.prediction_date:
            raise ValueError(
                "Prediction and outcome prediction_date values must match."
            )


@dataclass(frozen=True, slots=True)
class BacktestDiagnostics:
    prediction_dates_generated: int
    predictions_generated: int
    outcomes_generated: int
    missing_observations: int
    missing_outcomes: int
    filtered_predictions: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BacktestDataset:
    """Reproducible prediction and outcome records for one backtest."""

    backtest_id: str
    predictions: tuple[PredictionRecord, ...]
    outcomes: tuple[OutcomeRecord, ...]
    pairs_by_horizon: Mapping[int, tuple[PredictionOutcomePair, ...]]
    diagnostics: BacktestDiagnostics

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pairs_by_horizon",
            MappingProxyType(dict(self.pairs_by_horizon)),
        )
