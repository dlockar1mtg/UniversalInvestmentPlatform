"""Immutable models for probabilistic forecast distributions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from math import isclose, isfinite
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from ..models import ForecastHorizon
from .distribution_enums import (
    DistributionFamily,
    DistributionStatus,
    TailRiskSide,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _require_finite(name: str, value: float | None) -> None:
    if value is not None and not isfinite(float(value)):
        raise ValueError(f"{name} must be finite.")


def _require_probability(name: str, value: float) -> None:
    _require_finite(name, value)
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class ForecastPercentile:
    """One percentile of a forecast value distribution."""

    probability: float
    value: float
    label: str | None = None

    def __post_init__(self) -> None:
        _require_probability("probability", self.probability)
        _require_finite("value", self.value)
        if self.label is not None and not self.label.strip():
            raise ValueError("Percentile label cannot be empty.")


@dataclass(frozen=True, slots=True)
class ForecastConfidenceInterval:
    """Central interval extracted from a probability distribution."""

    lower_probability: float
    upper_probability: float
    lower_value: float
    upper_value: float
    coverage: float

    def __post_init__(self) -> None:
        for name in (
            "lower_probability",
            "upper_probability",
            "coverage",
        ):
            _require_probability(name, getattr(self, name))
        _require_finite("lower_value", self.lower_value)
        _require_finite("upper_value", self.upper_value)

        if self.lower_probability >= self.upper_probability:
            raise ValueError(
                "lower_probability must be below upper_probability."
            )
        expected_coverage = self.upper_probability - self.lower_probability
        if abs(expected_coverage - self.coverage) > 1e-9:
            raise ValueError(
                "coverage must equal upper_probability - lower_probability."
            )
        if self.lower_value > self.upper_value:
            raise ValueError("lower_value cannot exceed upper_value.")


@dataclass(frozen=True, slots=True)
class DistributionStatistics:
    """Summary statistics for the forecast value distribution."""

    mean: float
    median: float
    variance: float
    standard_deviation: float
    minimum: float
    maximum: float
    skewness: float | None = None
    excess_kurtosis: float | None = None
    mode: float | None = None
    sample_count: int | None = None

    def __post_init__(self) -> None:
        for name in (
            "mean",
            "median",
            "variance",
            "standard_deviation",
            "minimum",
            "maximum",
            "skewness",
            "excess_kurtosis",
            "mode",
        ):
            _require_finite(name, getattr(self, name))

        if self.variance < 0:
            raise ValueError("variance cannot be negative.")
        if self.standard_deviation < 0:
            raise ValueError("standard_deviation cannot be negative.")
        if self.minimum > self.maximum:
            raise ValueError("minimum cannot exceed maximum.")

        # Numerical outputs from deterministic simulations can differ by tiny
        # floating-point amounts even when they are mathematically identical.
        tolerance = 1e-12

        if (
            self.median < self.minimum - tolerance
            or self.median > self.maximum + tolerance
        ):
            raise ValueError("median must lie within minimum and maximum.")

        if (
            self.mean < self.minimum - tolerance
            or self.mean > self.maximum + tolerance
        ):
            raise ValueError("mean must lie within minimum and maximum.")

        if self.mode is not None and (
            self.mode < self.minimum - tolerance
            or self.mode > self.maximum + tolerance
        ):
            raise ValueError("mode must lie within minimum and maximum.")

        if self.sample_count is not None and self.sample_count <= 0:
            raise ValueError("sample_count must be positive.")


@dataclass(frozen=True, slots=True)
class TailRiskMetrics:
    """Value at Risk and Expected Shortfall for forecast returns."""

    confidence_level: float
    side: TailRiskSide
    value_at_risk: float
    expected_shortfall: float
    probability_of_loss: float
    probability_of_target_shortfall: float | None = None
    target_return: float | None = None

    def __post_init__(self) -> None:
        _require_probability("confidence_level", self.confidence_level)
        if self.confidence_level <= 0.5:
            raise ValueError("confidence_level must be greater than 0.5.")
        _require_finite("value_at_risk", self.value_at_risk)
        _require_finite("expected_shortfall", self.expected_shortfall)
        _require_probability("probability_of_loss", self.probability_of_loss)
        if self.probability_of_target_shortfall is not None:
            _require_probability(
                "probability_of_target_shortfall",
                self.probability_of_target_shortfall,
            )
        _require_finite("target_return", self.target_return)

        if self.side is TailRiskSide.LOWER:
            if (
                self.expected_shortfall > self.value_at_risk
                and not isclose(
                    self.expected_shortfall,
                    self.value_at_risk,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                raise ValueError(
                    "Lower-tail expected_shortfall cannot exceed value_at_risk."
                )
        elif self.side is TailRiskSide.UPPER:
            if (
                self.expected_shortfall < self.value_at_risk
                and not isclose(
                    self.expected_shortfall,
                    self.value_at_risk,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                raise ValueError(
                    "Upper-tail expected_shortfall cannot be below value_at_risk."
                )

        if (
            self.probability_of_target_shortfall is not None
            and self.target_return is None
        ):
            raise ValueError(
                "target_return is required when target shortfall probability "
                "is supplied."
            )


@dataclass(frozen=True, slots=True)
class DistributionProvenance:
    """Audit metadata describing distribution generation."""

    model_name: str
    model_version: str
    generated_at: datetime = field(default_factory=_utc_now)
    source_forecast_ids: tuple[str, ...] = ()
    source_run_id: str | None = None
    random_seed: int | None = None
    simulation_count: int | None = None
    code_commit: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_name.strip():
            raise ValueError("model_name is required.")
        if not self.model_version.strip():
            raise ValueError("model_version is required.")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")
        if self.simulation_count is not None and self.simulation_count <= 0:
            raise ValueError("simulation_count must be positive.")
        object.__setattr__(
            self,
            "parameters",
            _freeze_mapping(self.parameters),
        )


@dataclass(frozen=True, slots=True)
class ForecastDistributionResult:
    """Canonical probabilistic forecast distribution contract."""

    asset_id: str
    asset_class: str
    as_of_date: date
    target_date: date
    horizon: ForecastHorizon
    reference_value: float
    currency: str
    family: DistributionFamily
    statistics: DistributionStatistics
    provenance: DistributionProvenance

    distribution_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = "1.0.0"
    status: DistributionStatus = DistributionStatus.DRAFT
    percentiles: tuple[ForecastPercentile, ...] = ()
    confidence_intervals: tuple[ForecastConfidenceInterval, ...] = ()
    tail_risk: tuple[TailRiskMetrics, ...] = ()
    probability_above_reference: float | None = None
    probability_below_reference: float | None = None
    probability_above_target: float | None = None
    target_value: float | None = None
    notes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "distribution_id",
            "asset_id",
            "asset_class",
            "currency",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required.")
        if self.target_date <= self.as_of_date:
            raise ValueError("target_date must be after as_of_date.")
        _require_finite("reference_value", self.reference_value)
        if self.reference_value < 0:
            raise ValueError("reference_value cannot be negative.")

        for name in (
            "probability_above_reference",
            "probability_below_reference",
            "probability_above_target",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_probability(name, value)

        if (
            self.probability_above_reference is not None
            and self.probability_below_reference is not None
            and self.probability_above_reference
            + self.probability_below_reference
            > 1.0 + 1e-9
        ):
            raise ValueError(
                "Reference probabilities cannot sum to more than 1.0."
            )

        _require_finite("target_value", self.target_value)
        if (
            self.probability_above_target is not None
            and self.target_value is None
        ):
            raise ValueError(
                "target_value is required when probability_above_target "
                "is supplied."
            )

        percentile_probabilities = [
            item.probability for item in self.percentiles
        ]
        if len(percentile_probabilities) != len(set(percentile_probabilities)):
            raise ValueError("Percentile probabilities must be unique.")
        ordered = sorted(
            self.percentiles,
            key=lambda item: item.probability,
        )
        for earlier, later in zip(ordered, ordered[1:]):
            if earlier.value > later.value:
                raise ValueError(
                    "Percentile values must be nondecreasing by probability."
                )

        interval_keys = [
            (item.lower_probability, item.upper_probability)
            for item in self.confidence_intervals
        ]
        if len(interval_keys) != len(set(interval_keys)):
            raise ValueError("Confidence intervals must be unique.")

        tail_keys = [
            (item.confidence_level, item.side)
            for item in self.tail_risk
        ]
        if len(tail_keys) != len(set(tail_keys)):
            raise ValueError("Tail-risk metric keys must be unique.")

        object.__setattr__(
            self,
            "metadata",
            _freeze_mapping(self.metadata),
        )

    def percentile(self, probability: float) -> ForecastPercentile:
        """Return an exact percentile by probability."""

        for item in self.percentiles:
            if abs(item.probability - probability) <= 1e-12:
                return item
        raise KeyError(f"Percentile not available: {probability}")

    def central_interval(
        self,
        coverage: float,
    ) -> ForecastConfidenceInterval:
        """Return an exact central interval by coverage."""

        for item in self.confidence_intervals:
            if abs(item.coverage - coverage) <= 1e-12:
                return item
        raise KeyError(f"Confidence interval not available: {coverage}")
