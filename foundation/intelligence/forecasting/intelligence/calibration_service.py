"""Service for applying confidence calibration to universal forecasts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from ..models import UniversalForecast
from .calibration_contracts import (
    ConfidenceCalibrationEvidence,
    ConfidenceCalibrationRequest,
    ConfidenceCalibrationResult,
    MarketRegime,
)
from .calibration_engine import AdaptiveConfidenceCalibrationEngine
from .consensus_contracts import ForecastConsensusResult
from .quality_contracts import ForecastQualityScore


class ForecastConfidenceCalibrationService:
    """Calibrate a UniversalForecast and return an updated immutable record."""

    def __init__(
        self,
        engine: AdaptiveConfidenceCalibrationEngine | None = None,
    ) -> None:
        self.engine = engine or AdaptiveConfidenceCalibrationEngine()

    def calibrate_forecast(
        self,
        forecast: UniversalForecast,
        *,
        asset_class: str,
        regime: MarketRegime,
        quality_score: ForecastQualityScore,
        consensus_result: ForecastConsensusResult,
        evidence_records: Iterable[ConfidenceCalibrationEvidence],
    ) -> tuple[UniversalForecast, ConfidenceCalibrationResult]:
        if forecast.confidence_score is None:
            raise ValueError(
                "Forecast must include confidence_score before calibration."
            )

        model_key = (
            forecast.provenance.model_name,
            forecast.provenance.model_version,
        )
        if quality_score.evidence.model_key != model_key:
            raise ValueError(
                "Quality score does not match forecast provenance."
            )
        if consensus_result.asset_id != forecast.asset_id:
            raise ValueError(
                "Consensus result does not match forecast asset_id."
            )
        if consensus_result.horizon is not forecast.horizon:
            raise ValueError(
                "Consensus result does not match forecast horizon."
            )

        request = ConfidenceCalibrationRequest(
            engine_name=model_key[0],
            engine_version=model_key[1],
            asset_class=asset_class,
            horizon=forecast.horizon,
            regime=regime,
            as_of_date=forecast.as_of_date,
            raw_confidence=forecast.confidence_score,
            consensus_score=consensus_result.consensus_score,
            model_quality_score=quality_score.adjusted_score,
        )
        result = self.engine.calibrate(
            request,
            evidence_records,
        )

        metadata = dict(forecast.metadata)
        metadata["confidence_calibration"] = {
            "raw_confidence": result.raw_confidence,
            "calibrated_confidence": result.calibrated_confidence,
            "adjustment": result.adjustment,
            "strength": result.strength.value,
            "regime": regime.value,
        }

        updated = replace(
            forecast,
            confidence_score=result.calibrated_confidence,
            notes=forecast.notes + result.explanation,
            metadata=metadata,
        )
        return updated, result
