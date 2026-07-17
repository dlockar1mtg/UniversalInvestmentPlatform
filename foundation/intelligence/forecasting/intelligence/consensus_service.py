"""Service for building consensus inputs from universal forecasts."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import UniversalForecast
from .consensus_contracts import (
    ForecastConsensusInput,
    ForecastConsensusResult,
)
from .consensus_engine import ForecastConsensusEngine
from .quality_contracts import ForecastQualityScore


class ForecastConsensusService:
    """Join model forecasts with quality scores and run consensus analysis."""

    def __init__(
        self,
        engine: ForecastConsensusEngine | None = None,
    ) -> None:
        self.engine = engine or ForecastConsensusEngine()

    def analyze(
        self,
        forecasts: Iterable[UniversalForecast],
        quality_scores: Iterable[ForecastQualityScore],
        *,
        asset_class: str,
    ) -> ForecastConsensusResult:
        quality_by_model = {
            score.evidence.model_key: score
            for score in quality_scores
        }

        inputs: list[ForecastConsensusInput] = []
        missing_quality: list[str] = []

        for forecast in forecasts:
            model_key = (
                forecast.provenance.model_name,
                forecast.provenance.model_version,
            )
            quality = quality_by_model.get(model_key)
            if quality is None:
                missing_quality.append(
                    f"{model_key[0]} {model_key[1]}"
                )
                continue

            inputs.append(
                ForecastConsensusInput(
                    engine_name=model_key[0],
                    engine_version=model_key[1],
                    asset_id=forecast.asset_id,
                    asset_class=asset_class,
                    horizon=forecast.horizon,
                    reference_value=forecast.reference_value,
                    point_forecast=forecast.point_forecast,
                    direction=forecast.direction,
                    model_quality=quality.adjusted_score,
                    model_confidence=forecast.confidence_score,
                    metadata={
                        "forecast_id": forecast.forecast_id,
                        "quality_grade": quality.grade.value,
                        "quality_eligible": quality.eligible,
                    },
                )
            )

        if missing_quality:
            joined = ", ".join(sorted(missing_quality))
            raise ValueError(
                "Missing quality score for forecast models: "
                f"{joined}."
            )

        return self.engine.analyze(inputs)
