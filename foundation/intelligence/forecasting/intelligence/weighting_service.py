"""Service for building ensemble weighting signals from intelligence outputs."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import UniversalForecast
from .calibration_contracts import (
    ConfidenceCalibrationResult,
    MarketRegime,
)
from .consensus_contracts import ForecastConsensusResult
from .quality_contracts import ForecastQualityScore
from .weighting_contracts import (
    EnsembleModelSignal,
    EnsembleWeightResult,
)
from .weighting_engine import EnsembleWeightOptimizationEngine


class EnsembleWeightOptimizationService:
    """Join forecast intelligence outputs and optimize model weights."""

    def __init__(
        self,
        engine: EnsembleWeightOptimizationEngine | None = None,
    ) -> None:
        self.engine = engine or EnsembleWeightOptimizationEngine()

    def optimize(
        self,
        forecasts: Iterable[UniversalForecast],
        quality_scores: Iterable[ForecastQualityScore],
        calibration_results: Iterable[ConfidenceCalibrationResult],
        *,
        consensus_result: ForecastConsensusResult,
        asset_class: str,
        regime: MarketRegime,
    ) -> EnsembleWeightResult:
        forecast_items = tuple(forecasts)
        quality_by_model = {
            score.evidence.model_key: score
            for score in quality_scores
        }

        calibration_items = tuple(calibration_results)
        if len(calibration_items) != len(forecast_items):
            raise ValueError(
                "Each forecast requires one calibration result."
            )

        signals: list[EnsembleModelSignal] = []

        for forecast, calibration in zip(
            forecast_items,
            calibration_items,
        ):
            model_key = (
                forecast.provenance.model_name,
                forecast.provenance.model_version,
            )
            quality = quality_by_model.get(model_key)
            if quality is None:
                raise ValueError(
                    "Missing quality score for forecast model "
                    f"{model_key[0]} {model_key[1]}."
                )

            alignment = self._consensus_alignment(
                forecast.point_forecast,
                consensus_result.consensus_value,
            )

            signals.append(
                EnsembleModelSignal(
                    engine_name=model_key[0],
                    engine_version=model_key[1],
                    asset_class=asset_class,
                    horizon=forecast.horizon,
                    regime=regime,
                    model_quality_score=quality.adjusted_score,
                    calibrated_confidence=(
                        calibration.calibrated_confidence
                    ),
                    consensus_alignment_score=alignment,
                    reliability_score=calibration.reliability_score,
                    regime_match_score=calibration.regime_match_score,
                    eligible=quality.eligible,
                    metadata={
                        "forecast_id": forecast.forecast_id,
                        "quality_grade": quality.grade.value,
                        "calibration_strength": (
                            calibration.strength.value
                        ),
                    },
                )
            )

        return self.engine.optimize(signals)

    @staticmethod
    def _consensus_alignment(
        point_forecast: float,
        consensus_value: float | None,
    ) -> float:
        if consensus_value is None:
            return 0.0
        scale = max(abs(consensus_value), 1.0)
        relative_deviation = abs(
            point_forecast - consensus_value
        ) / scale
        return max(0.0, 1.0 - relative_deviation)
