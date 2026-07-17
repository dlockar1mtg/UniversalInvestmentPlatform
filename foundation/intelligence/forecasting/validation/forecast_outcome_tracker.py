"""Forecast-to-outcome matching and validation calculations."""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import ForecastDirection, UniversalForecast
from .forecast_validation_contracts import (
    ForecastOutcome,
    ForecastValidationRecord,
    ValidationStatus,
)


class ForecastOutcomeTracker:
    """Convert a forecast and realized outcome into a validation record."""

    def validate(
        self,
        forecast: UniversalForecast,
        outcome: ForecastOutcome,
    ) -> ForecastValidationRecord:
        self._validate_match(forecast, outcome)

        observed = outcome.observed_value
        predicted = forecast.point_forecast
        signed_error = predicted - observed
        absolute_error = abs(signed_error)

        relative_error = (
            None if observed == 0 else signed_error / observed
        )
        absolute_percentage_error = (
            None if observed == 0 else absolute_error / observed
        )

        realized_return = (
            None
            if forecast.reference_value == 0
            else observed / forecast.reference_value - 1.0
        )
        forecast_return = (
            None
            if forecast.reference_value == 0
            else predicted / forecast.reference_value - 1.0
        )

        direction_correct = self._direction_correct(
            forecast=forecast,
            realized_return=realized_return,
        )
        interval_coverage = self._interval_coverage(
            forecast=forecast,
            observed_value=observed,
        )
        scenario_hit = self._scenario_hit(
            forecast=forecast,
            observed_value=observed,
        )

        return ForecastValidationRecord(
            forecast=forecast,
            outcome=outcome,
            status=ValidationStatus.VALIDATED,
            validated_at=datetime.now(timezone.utc),
            absolute_error=absolute_error,
            signed_error=signed_error,
            relative_error=relative_error,
            absolute_percentage_error=absolute_percentage_error,
            realized_return=realized_return,
            forecast_return=forecast_return,
            direction_correct=direction_correct,
            interval_coverage=interval_coverage,
            scenario_hit=scenario_hit,
            metadata={
                "forecast_model": forecast.provenance.model_name,
                "forecast_model_version": (
                    forecast.provenance.model_version
                ),
                "outcome_source": outcome.source,
            },
        )

    @staticmethod
    def _validate_match(
        forecast: UniversalForecast,
        outcome: ForecastOutcome,
    ) -> None:
        if forecast.forecast_id != outcome.forecast_id:
            raise ValueError(
                "Outcome forecast_id does not match forecast."
            )
        if forecast.asset_id != outcome.asset_id:
            raise ValueError(
                "Outcome asset_id does not match forecast."
            )
        if outcome.observation_date < forecast.target_date:
            raise ValueError(
                "Outcome observation_date cannot precede target_date."
            )

    @staticmethod
    def _direction_correct(
        *,
        forecast: UniversalForecast,
        realized_return: float | None,
    ) -> bool | None:
        if realized_return is None:
            return None

        if forecast.direction is ForecastDirection.UP:
            return realized_return > 0
        if forecast.direction is ForecastDirection.DOWN:
            return realized_return < 0
        if forecast.direction is ForecastDirection.FLAT:
            return abs(realized_return) <= 1e-12
        return None

    @staticmethod
    def _interval_coverage(
        *,
        forecast: UniversalForecast,
        observed_value: float,
    ) -> dict[float, bool]:
        if forecast.interval is None:
            return {}

        return {
            forecast.interval.coverage: (
                forecast.interval.lower
                <= observed_value
                <= forecast.interval.upper
            )
        }

    @staticmethod
    def _scenario_hit(
        *,
        forecast: UniversalForecast,
        observed_value: float,
    ) -> str | None:
        if not forecast.scenarios:
            return None

        nearest = min(
            forecast.scenarios,
            key=lambda item: (
                abs(item.target_value - observed_value),
                item.scenario.value,
            ),
        )
        return nearest.scenario.value
