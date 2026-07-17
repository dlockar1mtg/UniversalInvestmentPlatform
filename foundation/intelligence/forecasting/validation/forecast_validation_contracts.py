"""Contracts for forecast outcome tracking and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from ..models import UniversalForecast


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _require_finite(name: str, value: float | None) -> None:
    if value is not None and not isfinite(float(value)):
        raise ValueError(f"{name} must be finite.")


class OutcomeCompleteness(str, Enum):
    """Completeness state for observed forecast outcomes."""

    PARTIAL = "partial"
    COMPLETE = "complete"


class ValidationStatus(str, Enum):
    """Lifecycle status of a forecast validation record."""

    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ForecastOutcome:
    """Observed outcome associated with a forecast target."""

    forecast_id: str
    asset_id: str
    observation_date: date
    observed_value: float
    completeness: OutcomeCompleteness = OutcomeCompleteness.COMPLETE
    realized_volatility: float | None = None
    realized_max_drawdown: float | None = None
    source: str = "unknown"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.forecast_id.strip():
            raise ValueError("forecast_id is required.")
        if not self.asset_id.strip():
            raise ValueError("asset_id is required.")
        if not self.source.strip():
            raise ValueError("source is required.")
        _require_finite("observed_value", self.observed_value)
        if self.observed_value < 0:
            raise ValueError("observed_value cannot be negative.")
        _require_finite("realized_volatility", self.realized_volatility)
        _require_finite(
            "realized_max_drawdown",
            self.realized_max_drawdown,
        )
        if (
            self.realized_volatility is not None
            and self.realized_volatility < 0
        ):
            raise ValueError(
                "realized_volatility cannot be negative."
            )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ForecastValidationRecord:
    """Permanent record linking one forecast to one realized outcome."""

    forecast: UniversalForecast
    outcome: ForecastOutcome
    status: ValidationStatus
    validated_at: datetime = field(default_factory=_utc_now)

    absolute_error: float | None = None
    signed_error: float | None = None
    relative_error: float | None = None
    absolute_percentage_error: float | None = None
    realized_return: float | None = None
    forecast_return: float | None = None
    direction_correct: bool | None = None
    interval_coverage: Mapping[float, bool] = field(default_factory=dict)
    scenario_hit: str | None = None
    notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.validated_at.tzinfo is None:
            raise ValueError("validated_at must be timezone-aware.")
        if self.forecast.forecast_id != self.outcome.forecast_id:
            raise ValueError(
                "Forecast and outcome forecast_id values must match."
            )
        if self.forecast.asset_id != self.outcome.asset_id:
            raise ValueError(
                "Forecast and outcome asset_id values must match."
            )
        if self.outcome.observation_date < self.forecast.target_date:
            raise ValueError(
                "Outcome observation_date cannot precede target_date."
            )

        for name in (
            "absolute_error",
            "signed_error",
            "relative_error",
            "absolute_percentage_error",
            "realized_return",
            "forecast_return",
        ):
            _require_finite(name, getattr(self, name))

        for coverage, covered in self.interval_coverage.items():
            _require_finite("interval coverage key", coverage)
            if not 0.0 <= float(coverage) <= 1.0:
                raise ValueError(
                    "Interval coverage keys must be between 0 and 1."
                )
            if not isinstance(covered, bool):
                raise ValueError(
                    "Interval coverage values must be booleans."
                )

        object.__setattr__(
            self,
            "interval_coverage",
            _freeze_mapping(self.interval_coverage),
        )
        object.__setattr__(
            self,
            "metadata",
            _freeze_mapping(self.metadata),
        )
