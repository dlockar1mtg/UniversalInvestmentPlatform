"""In-memory immutable-history archive for forecast validation records."""

from __future__ import annotations

from collections.abc import Iterable

from .forecast_validation_contracts import ForecastValidationRecord


class ForecastArchive:
    """Store and retrieve validated forecast outcomes."""

    def __init__(self) -> None:
        self._records: dict[str, ForecastValidationRecord] = {}

    def add(
        self,
        record: ForecastValidationRecord,
    ) -> None:
        forecast_id = record.forecast.forecast_id
        if forecast_id in self._records:
            raise ValueError(
                f"Forecast already archived: {forecast_id}"
            )
        self._records[forecast_id] = record

    def get(
        self,
        forecast_id: str,
    ) -> ForecastValidationRecord:
        try:
            return self._records[forecast_id]
        except KeyError as exc:
            raise KeyError(
                f"Forecast validation not found: {forecast_id}"
            ) from exc

    def contains(
        self,
        forecast_id: str,
    ) -> bool:
        return forecast_id in self._records

    def all(
        self,
    ) -> tuple[ForecastValidationRecord, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda item: (
                    item.forecast.target_date,
                    item.forecast.asset_id,
                    item.forecast.forecast_id,
                ),
            )
        )

    def by_asset(
        self,
        asset_id: str,
    ) -> tuple[ForecastValidationRecord, ...]:
        return tuple(
            item
            for item in self.all()
            if item.forecast.asset_id == asset_id
        )

    def by_model(
        self,
        model_name: str,
        model_version: str | None = None,
    ) -> tuple[ForecastValidationRecord, ...]:
        return tuple(
            item
            for item in self.all()
            if item.forecast.provenance.model_name == model_name
            and (
                model_version is None
                or item.forecast.provenance.model_version
                == model_version
            )
        )

    def extend(
        self,
        records: Iterable[ForecastValidationRecord],
    ) -> None:
        for record in records:
            self.add(record)

    def __len__(self) -> int:
        return len(self._records)
