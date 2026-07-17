"""Dataclass models for the universal forecast contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from math import isfinite
from typing import Any, Mapping
from uuid import uuid4

from .forecast_enums import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastScenario,
    ForecastStatus,
    IntervalType,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_finite(name: str, value: float | None) -> None:
    if value is not None and not isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number.")


def _require_probability(name: str, value: float | None) -> None:
    if value is None:
        return
    _require_finite(name, value)
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class ForecastInterval:
    """An uncertainty interval surrounding a forecast estimate."""

    lower: float
    upper: float
    coverage: float = 0.80
    interval_type: IntervalType = IntervalType.PREDICTION

    def __post_init__(self) -> None:
        _require_finite("lower", self.lower)
        _require_finite("upper", self.upper)
        _require_probability("coverage", self.coverage)
        if self.lower > self.upper:
            raise ValueError("ForecastInterval.lower cannot exceed upper.")


@dataclass(frozen=True, slots=True)
class ForecastDistribution:
    """Optional distribution summary, including Monte Carlo output."""

    distribution_name: str
    mean: float
    median: float
    standard_deviation: float
    minimum: float | None = None
    maximum: float | None = None
    sample_count: int | None = None
    quantiles: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.distribution_name.strip():
            raise ValueError("distribution_name is required.")

        for field_name in (
            "mean",
            "median",
            "standard_deviation",
            "minimum",
            "maximum",
        ):
            _require_finite(field_name, getattr(self, field_name))

        if self.standard_deviation < 0:
            raise ValueError("standard_deviation cannot be negative.")
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError("minimum cannot exceed maximum.")
        if self.sample_count is not None and self.sample_count <= 0:
            raise ValueError("sample_count must be greater than zero.")

        for name, value in self.quantiles.items():
            if not str(name).strip():
                raise ValueError("Quantile names cannot be empty.")
            _require_finite(f"quantiles[{name!r}]", value)


@dataclass(frozen=True, slots=True)
class ForecastScenarioResult:
    """One bear, base, or bull scenario result."""

    scenario: ForecastScenario
    target_value: float
    probability: float | None = None
    expected_return: float | None = None
    interval: ForecastInterval | None = None
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_finite("target_value", self.target_value)
        _require_probability("probability", self.probability)
        _require_finite("expected_return", self.expected_return)


@dataclass(frozen=True, slots=True)
class ForecastProvenance:
    """Audit metadata describing how the forecast was generated."""

    model_name: str
    model_version: str
    method: ForecastMethod
    generated_at: datetime = field(default_factory=_utc_now)
    training_data_start: date | None = None
    training_data_end: date | None = None
    source_run_id: str | None = None
    source_dataset_ids: tuple[str, ...] = ()
    feature_set_version: str | None = None
    code_commit: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            raise ValueError("model_name is required.")
        if not self.model_version.strip():
            raise ValueError("model_version is required.")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")
        if (
            self.training_data_start is not None
            and self.training_data_end is not None
            and self.training_data_start > self.training_data_end
        ):
            raise ValueError(
                "training_data_start cannot be after training_data_end."
            )


@dataclass(frozen=True, slots=True)
class UniversalForecast:
    """Canonical forecast returned by every platform forecasting model."""

    asset_id: str
    as_of_date: date
    target_date: date
    horizon: ForecastHorizon
    reference_value: float
    point_forecast: float
    currency: str
    provenance: ForecastProvenance

    forecast_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = "1.0.0"
    status: ForecastStatus = ForecastStatus.DRAFT
    direction: ForecastDirection = ForecastDirection.UNKNOWN
    confidence_score: float | None = None
    expected_return: float | None = None
    interval: ForecastInterval | None = None
    distribution: ForecastDistribution | None = None
    scenarios: tuple[ForecastScenarioResult, ...] = ()
    calibration_score: float | None = None
    backtest_run_id: str | None = None
    notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.forecast_id.strip():
            raise ValueError("forecast_id is required.")
        if not self.asset_id.strip():
            raise ValueError("asset_id is required.")
        if not self.currency.strip():
            raise ValueError("currency is required.")
        if self.target_date <= self.as_of_date:
            raise ValueError("target_date must be after as_of_date.")

        _require_finite("reference_value", self.reference_value)
        _require_finite("point_forecast", self.point_forecast)
        _require_probability("confidence_score", self.confidence_score)
        _require_probability("calibration_score", self.calibration_score)
        _require_finite("expected_return", self.expected_return)

        scenario_names = [scenario.scenario for scenario in self.scenarios]
        if len(scenario_names) != len(set(scenario_names)):
            raise ValueError("Each scenario may appear only once.")

        probabilities = [
            scenario.probability
            for scenario in self.scenarios
            if scenario.probability is not None
        ]
        if probabilities and len(probabilities) == len(self.scenarios):
            if abs(sum(probabilities) - 1.0) > 1e-6:
                raise ValueError(
                    "Scenario probabilities must sum to 1.0 when all are supplied."
                )

    def to_dict(self) -> dict[str, Any]:
        """Return a recursively serialized dictionary."""

        return asdict(self)
