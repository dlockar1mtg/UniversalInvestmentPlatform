"""Service integration for scenario-tree generation."""

from __future__ import annotations

from ..models import UniversalForecast
from .scenario_contracts import (
    ScenarioStageDefinition,
    ScenarioTreeProfile,
    ScenarioTreeRequest,
    ScenarioTreeResult,
)
from .scenario_tree_engine import ScenarioTreeGenerationEngine


class ScenarioTreeForecastService:
    """Generate a scenario tree from a UniversalForecast context."""

    def __init__(
        self,
        engine: ScenarioTreeGenerationEngine | None = None,
    ) -> None:
        self.engine = engine or ScenarioTreeGenerationEngine()

    def generate_for_forecast(
        self,
        forecast: UniversalForecast,
        *,
        asset_class: str,
        stages: tuple[ScenarioStageDefinition, ...],
        profile: ScenarioTreeProfile | None = None,
    ) -> ScenarioTreeResult:
        request = ScenarioTreeRequest(
            asset_id=forecast.asset_id,
            asset_class=asset_class,
            as_of_date=forecast.as_of_date,
            target_date=forecast.target_date,
            horizon=forecast.horizon,
            reference_value=forecast.reference_value,
            currency=forecast.currency,
            model_name=forecast.provenance.model_name,
            model_version=forecast.provenance.model_version,
            stages=stages,
            profile=profile or ScenarioTreeProfile(),
            metadata={
                "source_forecast_id": forecast.forecast_id,
                "point_forecast": forecast.point_forecast,
                "forecast_confidence": forecast.confidence_score,
            },
        )
        return self.engine.generate(request)
