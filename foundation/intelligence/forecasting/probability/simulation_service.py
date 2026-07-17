"""Service wrapper for Monte Carlo probabilistic forecasting."""

from __future__ import annotations

from dataclasses import replace

from ..models import UniversalForecast
from .simulation_contracts import (
    MonteCarloSimulationProfile,
    MonteCarloSimulationRequest,
    MonteCarloSimulationResult,
)
from .simulation_engine import MonteCarloSimulationEngine


class MonteCarloForecastService:
    """Build and execute simulation requests from UniversalForecast objects."""

    def __init__(
        self,
        engine: MonteCarloSimulationEngine | None = None,
    ) -> None:
        self.engine = engine or MonteCarloSimulationEngine()

    def simulate_forecast(
        self,
        forecast: UniversalForecast,
        *,
        asset_class: str,
        profile: MonteCarloSimulationProfile | None = None,
        target_value: float | None = None,
        source_run_id: str | None = None,
    ) -> MonteCarloSimulationResult:
        if forecast.reference_value <= 0:
            raise ValueError(
                "Forecast reference_value must be positive."
            )

        simulation_profile = profile or MonteCarloSimulationProfile(
            annual_drift=forecast.expected_return or 0.0,
        )

        request = MonteCarloSimulationRequest(
            asset_id=forecast.asset_id,
            asset_class=asset_class,
            as_of_date=forecast.as_of_date,
            target_date=forecast.target_date,
            horizon=forecast.horizon,
            reference_value=forecast.reference_value,
            currency=forecast.currency,
            model_name=forecast.provenance.model_name,
            model_version=forecast.provenance.model_version,
            source_forecast_ids=(forecast.forecast_id,),
            source_run_id=source_run_id,
            target_value=target_value,
            profile=simulation_profile,
            metadata={
                "point_forecast": forecast.point_forecast,
                "forecast_confidence": forecast.confidence_score,
            },
        )
        return self.engine.simulate(request)
