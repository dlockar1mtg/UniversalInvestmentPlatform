"""Integration service for complete forecast explanations."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import UniversalForecast
from .attribution_engine import ForecastDriverAttributionEngine
from .calibration_contracts import ConfidenceCalibrationResult, MarketRegime
from .consensus_contracts import ForecastConsensusResult
from .evidence_graph import ForecastEvidenceGraphBuilder
from .explainability_contracts import (
    ForecastExplanation,
    ForecastRiskFactor,
)
from .historical_similarity import HistoricalSimilarityEngine
from .narrative_engine import ForecastNarrativeEngine
from .quality_contracts import ForecastQualityScore
from .weighting_contracts import EnsembleWeightResult


class ExplainableForecastIntelligenceService:
    """Build a complete deterministic explanation for one forecast."""

    def __init__(
        self,
        *,
        attribution_engine: ForecastDriverAttributionEngine | None = None,
        similarity_engine: HistoricalSimilarityEngine | None = None,
        graph_builder: ForecastEvidenceGraphBuilder | None = None,
        narrative_engine: ForecastNarrativeEngine | None = None,
    ) -> None:
        self.attribution_engine = (
            attribution_engine or ForecastDriverAttributionEngine()
        )
        self.similarity_engine = (
            similarity_engine or HistoricalSimilarityEngine()
        )
        self.graph_builder = graph_builder or ForecastEvidenceGraphBuilder()
        self.narrative_engine = narrative_engine or ForecastNarrativeEngine()

    def explain(
        self,
        forecast: UniversalForecast,
        *,
        asset_class: str,
        quality_score: ForecastQualityScore,
        consensus_result: ForecastConsensusResult,
        calibration_result: ConfidenceCalibrationResult,
        weight_result: EnsembleWeightResult,
        raw_driver_contributions: Iterable[tuple[str, float, str]],
        risks: Iterable[ForecastRiskFactor],
        current_features: dict[str, float],
        historical_candidates: Iterable[
            tuple[str, str, MarketRegime, str, dict[str, float]]
        ],
        analog_limit: int = 3,
    ) -> ForecastExplanation:
        self._validate_context(
            forecast=forecast,
            quality_score=quality_score,
            consensus_result=consensus_result,
            weight_result=weight_result,
        )

        drivers = self.attribution_engine.attribute(
            raw_driver_contributions
        )
        ranked_risks = self.attribution_engine.rank_risks(risks)
        analogs = self.similarity_engine.rank(
            current_features=current_features,
            candidates=historical_candidates,
            limit=analog_limit,
        )

        ensemble_weights = {
            f"{item.engine_name} {item.engine_version}": (
                item.constrained_weight
            )
            for item in weight_result.weights
        }
        leading_model = (
            next(iter(ensemble_weights))
            if ensemble_weights
            else None
        )

        graph = self.graph_builder.build(
            forecast_id=forecast.forecast_id,
            quality_score=quality_score.adjusted_score,
            consensus_score=consensus_result.consensus_score,
            calibration_score=calibration_result.calibrated_confidence,
            ensemble_weights=ensemble_weights,
            drivers=drivers,
            risks=ranked_risks,
            analogs=analogs,
        )
        narrative = self.narrative_engine.generate(
            asset_id=forecast.asset_id,
            direction=forecast.direction,
            quality_score=quality_score.adjusted_score,
            consensus_score=consensus_result.consensus_score,
            calibrated_confidence=(
                calibration_result.calibrated_confidence
            ),
            drivers=drivers,
            risks=ranked_risks,
            analogs=analogs,
            leading_model=leading_model,
        )

        return ForecastExplanation(
            forecast_id=forecast.forecast_id,
            asset_id=forecast.asset_id,
            asset_class=asset_class,
            horizon=forecast.horizon,
            direction=forecast.direction,
            point_forecast=forecast.point_forecast,
            confidence=forecast.confidence_score,
            quality_score=quality_score.adjusted_score,
            consensus_score=consensus_result.consensus_score,
            calibrated_confidence=(
                calibration_result.calibrated_confidence
            ),
            ensemble_weights=ensemble_weights,
            drivers=drivers,
            risks=ranked_risks,
            historical_analogs=analogs,
            evidence_graph=graph,
            narrative=narrative,
            audit_metadata={
                "quality_grade": quality_score.grade.value,
                "consensus_strength": consensus_result.strength.value,
                "calibration_strength": (
                    calibration_result.strength.value
                ),
                "weighting_status": weight_result.status.value,
            },
        )

    @staticmethod
    def _validate_context(
        *,
        forecast: UniversalForecast,
        quality_score: ForecastQualityScore,
        consensus_result: ForecastConsensusResult,
        weight_result: EnsembleWeightResult,
    ) -> None:
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
        if weight_result.horizon is not forecast.horizon:
            raise ValueError(
                "Weight result does not match forecast horizon."
            )
