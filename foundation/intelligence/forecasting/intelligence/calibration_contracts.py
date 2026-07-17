"""Contracts for adaptive forecast confidence calibration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from ..models import ForecastHorizon


def _validate_probability(name: str, value: float) -> None:
    if not isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class MarketRegime(str, Enum):
    """Supported market regimes for calibration evidence."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


class CalibrationStrength(str, Enum):
    """Human-readable strength of a calibration decision."""

    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class ConfidenceCalibrationProfile:
    """Rules controlling adaptive confidence calibration."""

    minimum_sample_size: int = 30
    target_sample_size: int = 250
    stale_after_days: int = 180
    maximum_positive_adjustment: float = 0.20
    maximum_negative_adjustment: float = 0.35
    consensus_weight: float = 0.30
    reliability_weight: float = 0.45
    regime_match_weight: float = 0.15
    freshness_weight: float = 0.10

    def __post_init__(self) -> None:
        if self.minimum_sample_size <= 0:
            raise ValueError("minimum_sample_size must be positive.")
        if self.target_sample_size < self.minimum_sample_size:
            raise ValueError(
                "target_sample_size cannot be below minimum_sample_size."
            )
        if self.stale_after_days <= 0:
            raise ValueError("stale_after_days must be positive.")
        _validate_probability(
            "maximum_positive_adjustment",
            self.maximum_positive_adjustment,
        )
        _validate_probability(
            "maximum_negative_adjustment",
            self.maximum_negative_adjustment,
        )

        weights = (
            self.consensus_weight,
            self.reliability_weight,
            self.regime_match_weight,
            self.freshness_weight,
        )
        for index, weight in enumerate(weights):
            _validate_probability(f"weight[{index}]", weight)
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("Calibration weights must sum to 1.0.")


@dataclass(frozen=True, slots=True)
class ConfidenceCalibrationEvidence:
    """Historical reliability evidence for one forecast context."""

    engine_name: str
    engine_version: str
    asset_class: str
    horizon: ForecastHorizon
    regime: MarketRegime
    evaluation_date: date
    sample_size: int
    mean_reported_confidence: float
    empirical_success_rate: float
    calibration_error: float
    interval_coverage: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "engine_name",
            "engine_version",
            "asset_class",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required.")
        if self.sample_size < 0:
            raise ValueError("sample_size cannot be negative.")
        for field_name in (
            "mean_reported_confidence",
            "empirical_success_rate",
            "calibration_error",
            "interval_coverage",
        ):
            _validate_probability(field_name, getattr(self, field_name))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @property
    def model_key(self) -> tuple[str, str]:
        return (self.engine_name, self.engine_version)

    @property
    def reliability_gap(self) -> float:
        return (
            self.empirical_success_rate
            - self.mean_reported_confidence
        )


@dataclass(frozen=True, slots=True)
class ConfidenceCalibrationRequest:
    """Inputs required to calibrate one forecast confidence value."""

    engine_name: str
    engine_version: str
    asset_class: str
    horizon: ForecastHorizon
    regime: MarketRegime
    as_of_date: date
    raw_confidence: float
    consensus_score: float
    model_quality_score: float

    def __post_init__(self) -> None:
        for field_name in (
            "engine_name",
            "engine_version",
            "asset_class",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required.")
        for field_name in (
            "raw_confidence",
            "consensus_score",
            "model_quality_score",
        ):
            _validate_probability(field_name, getattr(self, field_name))


@dataclass(frozen=True, slots=True)
class ConfidenceCalibrationResult:
    """Auditable result of adaptive confidence calibration."""

    raw_confidence: float
    calibrated_confidence: float
    adjustment: float
    reliability_score: float
    sample_factor: float
    freshness_factor: float
    regime_match_score: float
    evidence_count: int
    strength: CalibrationStrength
    selected_evidence: ConfidenceCalibrationEvidence | None
    explanation: tuple[str, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "raw_confidence",
            "calibrated_confidence",
            "reliability_score",
            "sample_factor",
            "freshness_factor",
            "regime_match_score",
        ):
            _validate_probability(field_name, getattr(self, field_name))
        if not -1.0 <= self.adjustment <= 1.0:
            raise ValueError("adjustment must be between -1.0 and 1.0.")
        if self.evidence_count < 0:
            raise ValueError("evidence_count cannot be negative.")
        object.__setattr__(self, "metrics", _freeze_mapping(self.metrics))
