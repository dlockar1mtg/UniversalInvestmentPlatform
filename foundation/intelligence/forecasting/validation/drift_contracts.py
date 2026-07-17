"""Contracts for forecast drift detection and regime memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _require_finite(name: str, value: float | None) -> None:
    if value is not None and not isfinite(float(value)):
        raise ValueError(f"{name} must be finite.")


def _require_probability(name: str, value: float | None) -> None:
    if value is None:
        return
    _require_finite(name, value)
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


class DriftType(str, Enum):
    """Supported forecast drift dimensions."""

    PERFORMANCE = "performance"
    ERROR = "error"
    BIAS = "bias"
    DIRECTION = "direction"
    CALIBRATION = "calibration"
    REGIME = "regime"


class DriftSeverity(str, Enum):
    """Qualitative drift severity."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DriftRecommendation(str, Enum):
    """Recommended action after drift evaluation."""

    NONE = "none"
    MONITOR = "monitor"
    RECALIBRATE = "recalibrate"
    REDUCE_WEIGHT = "reduce_weight"
    RETRAIN = "retrain"
    RETIRE = "retire"


@dataclass(frozen=True, slots=True)
class DriftDetectionProfile:
    """Configuration for forecast drift detection."""

    performance_weight: float = 0.30
    error_weight: float = 0.25
    bias_weight: float = 0.15
    direction_weight: float = 0.15
    calibration_weight: float = 0.15
    low_threshold: float = 0.15
    moderate_threshold: float = 0.30
    high_threshold: float = 0.50
    critical_threshold: float = 0.70
    minimum_sample_size: int = 3
    maximum_relative_error_change: float = 1.0
    regime_penalty: float = 0.10
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        weights = (
            self.performance_weight,
            self.error_weight,
            self.bias_weight,
            self.direction_weight,
            self.calibration_weight,
        )
        for index, value in enumerate(weights):
            _require_probability(f"weight[{index}]", value)
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("Drift factor weights must sum to 1.0.")

        thresholds = (
            self.low_threshold,
            self.moderate_threshold,
            self.high_threshold,
            self.critical_threshold,
        )
        for index, value in enumerate(thresholds):
            _require_probability(f"threshold[{index}]", value)
        if thresholds != tuple(sorted(thresholds)):
            raise ValueError("Drift thresholds must be ordered.")

        if self.minimum_sample_size <= 0:
            raise ValueError("minimum_sample_size must be positive.")
        if self.maximum_relative_error_change <= 0:
            raise ValueError(
                "maximum_relative_error_change must be positive."
            )
        _require_probability("regime_penalty", self.regime_penalty)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class DriftMetric:
    """One drift dimension and its normalized score."""

    drift_type: DriftType
    raw_change: float
    normalized_score: float
    explanation: str

    def __post_init__(self) -> None:
        _require_finite("raw_change", self.raw_change)
        _require_probability("normalized_score", self.normalized_score)
        if not self.explanation.strip():
            raise ValueError("explanation is required.")


@dataclass(frozen=True, slots=True)
class RegimePerformanceSnapshot:
    """Historical performance memory for one model and regime."""

    model_key: str
    regime: str
    as_of_date: date
    sample_size: int
    performance_score: float
    mae: float
    directional_accuracy: float | None
    interval_coverage: float | None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_key.strip():
            raise ValueError("model_key is required.")
        if not self.regime.strip():
            raise ValueError("regime is required.")
        if self.sample_size <= 0:
            raise ValueError("sample_size must be positive.")
        _require_probability("performance_score", self.performance_score)
        _require_probability(
            "directional_accuracy",
            self.directional_accuracy,
        )
        _require_probability(
            "interval_coverage",
            self.interval_coverage,
        )
        _require_finite("mae", self.mae)
        if self.mae < 0:
            raise ValueError("mae cannot be negative.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ForecastDriftSignal:
    """Drift result for one model."""

    model_key: str
    as_of_date: date
    baseline_sample_size: int
    current_sample_size: int
    baseline_regime: str
    current_regime: str
    metrics: tuple[DriftMetric, ...]
    drift_score: float
    severity: DriftSeverity
    recommendation: DriftRecommendation
    regime_changed: bool
    explanation: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_key.strip():
            raise ValueError("model_key is required.")
        if self.baseline_sample_size <= 0:
            raise ValueError(
                "baseline_sample_size must be positive."
            )
        if self.current_sample_size <= 0:
            raise ValueError(
                "current_sample_size must be positive."
            )
        if not self.baseline_regime.strip():
            raise ValueError("baseline_regime is required.")
        if not self.current_regime.strip():
            raise ValueError("current_regime is required.")
        _require_probability("drift_score", self.drift_score)
        if not self.metrics:
            raise ValueError("At least one drift metric is required.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class DriftHistoryEntry:
    """Persistent drift-history record."""

    model_key: str
    evaluated_at: datetime
    drift_score: float
    severity: DriftSeverity
    recommendation: DriftRecommendation
    baseline_regime: str
    current_regime: str
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_key.strip():
            raise ValueError("model_key is required.")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware.")
        _require_probability("drift_score", self.drift_score)
        object.__setattr__(self, "metrics", _freeze_mapping(self.metrics))


@dataclass(frozen=True, slots=True)
class DriftHistory:
    """Immutable collection of drift-history entries."""

    entries: tuple[DriftHistoryEntry, ...]
    generated_at: datetime = field(default_factory=_utc_now)
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")


@dataclass(frozen=True, slots=True)
class ForecastDriftReport:
    """Drift signals, regime memory, and updated history."""

    signals: tuple[ForecastDriftSignal, ...]
    regime_memory: tuple[RegimePerformanceSnapshot, ...]
    history: DriftHistory

    def __post_init__(self) -> None:
        signal_keys = [item.model_key for item in self.signals]
        if len(signal_keys) != len(set(signal_keys)):
            raise ValueError("Drift signal model keys must be unique.")
