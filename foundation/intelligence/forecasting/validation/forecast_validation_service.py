"""Service orchestration for forecast outcome tracking."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import UniversalForecast
from .forecast_archive import ForecastArchive
from .forecast_outcome_tracker import ForecastOutcomeTracker
from .forecast_validation_contracts import (
    ForecastOutcome,
    ForecastValidationRecord,
)


class ForecastValidationService:
    """Validate outcomes and persist immutable validation history."""

    def __init__(
        self,
        *,
        tracker: ForecastOutcomeTracker | None = None,
        archive: ForecastArchive | None = None,
    ) -> None:
        self.tracker = tracker or ForecastOutcomeTracker()
        self.archive = archive or ForecastArchive()

    def validate_and_archive(
        self,
        forecast: UniversalForecast,
        outcome: ForecastOutcome,
    ) -> ForecastValidationRecord:
        record = self.tracker.validate(forecast, outcome)
        self.archive.add(record)
        return record

    def validate_many(
        self,
        pairs: Iterable[
            tuple[UniversalForecast, ForecastOutcome]
        ],
    ) -> tuple[ForecastValidationRecord, ...]:
        records = tuple(
            self.tracker.validate(forecast, outcome)
            for forecast, outcome in pairs
        )

        existing = {
            item.forecast.forecast_id
            for item in self.archive.all()
        }
        incoming = [
            item.forecast.forecast_id
            for item in records
        ]
        if len(incoming) != len(set(incoming)):
            raise ValueError(
                "Duplicate forecast ids in validation batch."
            )
        overlap = existing.intersection(incoming)
        if overlap:
            raise ValueError(
                "Validation batch contains already archived forecasts: "
                + ", ".join(sorted(overlap))
            )

        self.archive.extend(records)
        return records
