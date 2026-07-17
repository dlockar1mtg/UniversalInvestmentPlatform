"""Contracts for cross-model forecast consensus intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from ..models import ForecastDirection, ForecastHorizon


def _validate_probability(name: str, value: float) -> None:
    if not isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class ConsensusStrength(str, Enum):
    """Human-readable level of cross-model agreement."""

    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    CONFLICTED = "conflicted"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class ConsensusProfile:
    """Thresholds and weights controlling consensus analysis."""

    value_agreement_weight: float = 0.55
    direction_agreement_weight: float = 0.30
    quality_agreement_weight: float = 0.15
    minimum_model_count: int = 2
    outlier_z_threshold: float = 2.5
    maximum_confidence_boost: float = 0.15
    maximum_confidence_penalty: float = 0.30

    def __post_init__(self) -> None:
        weights = (
            self.value_agreement_weight,
            self.direction_agreement_weight,
            self.quality_agreement_weight,
        )
        for index, weight in enumerate(weights):
            _validate_probability(f"weight[{index}]", weight)
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("Consensus weights must sum to 1.0.")
        if self.minimum_model_count < 2:
            raise ValueError("minimum_model_count must be at least 2.")
        if self.outlier_z_threshold <= 0:
            raise ValueError("outlier_z_threshold must be positive.")
        _validate_probability(
            "maximum_confidence_boost",
            self.maximum_confidence_boost,
        )
        _validate_probability(
            "maximum_confidence_penalty",
            self.maximum_confidence_penalty,
        )


@dataclass(frozen=True, slots=True)
class ForecastConsensusInput:
    """Comparable model forecast used in one consensus analysis."""

    engine_name: str
    engine_version: str
    asset_id: str
    asset_class: str
    horizon: ForecastHorizon
    reference_value: float
    point_forecast: float
    direction: ForecastDirection
    model_quality: float
    model_confidence: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "engine_name",
            "engine_version",
            "asset_id",
            "asset_class",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required.")
        for field_name in ("reference_value", "point_forecast"):
            value = getattr(self, field_name)
            if not isfinite(float(value)):
                raise ValueError(f"{field_name} must be finite.")
        _validate_probability("model_quality", self.model_quality)
        if self.model_confidence is not None:
            _validate_probability(
                "model_confidence",
                self.model_confidence,
            )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @property
    def model_key(self) -> tuple[str, str]:
        return (self.engine_name, self.engine_version)

    @property
    def expected_return(self) -> float | None:
        if self.reference_value == 0:
            return None
        return (self.point_forecast / self.reference_value) - 1.0


@dataclass(frozen=True, slots=True)
class ConsensusOutlier:
    """Model flagged as materially separated from the model group."""

    engine_name: str
    engine_version: str
    point_forecast: float
    robust_z_score: float
    deviation_from_consensus: float

    def __post_init__(self) -> None:
        for field_name in (
            "point_forecast",
            "robust_z_score",
            "deviation_from_consensus",
        ):
            if not isfinite(float(getattr(self, field_name))):
                raise ValueError(f"{field_name} must be finite.")


@dataclass(frozen=True, slots=True)
class ForecastConsensusResult:
    """Auditable result of a cross-model consensus calculation."""

    asset_id: str
    asset_class: str
    horizon: ForecastHorizon
    model_count: int
    consensus_value: float | None
    consensus_direction: ForecastDirection
    value_agreement_score: float
    direction_agreement_score: float
    quality_agreement_score: float
    consensus_score: float
    strength: ConsensusStrength
    dispersion_ratio: float | None
    confidence_adjustment: float
    outliers: tuple[ConsensusOutlier, ...] = ()
    explanation: tuple[str, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.model_count < 0:
            raise ValueError("model_count cannot be negative.")
        if self.consensus_value is not None and not isfinite(
            float(self.consensus_value)
        ):
            raise ValueError("consensus_value must be finite.")
        for field_name in (
            "value_agreement_score",
            "direction_agreement_score",
            "quality_agreement_score",
            "consensus_score",
        ):
            _validate_probability(field_name, getattr(self, field_name))
        if self.dispersion_ratio is not None and self.dispersion_ratio < 0:
            raise ValueError("dispersion_ratio cannot be negative.")
        if not -1.0 <= self.confidence_adjustment <= 1.0:
            raise ValueError(
                "confidence_adjustment must be between -1.0 and 1.0."
            )
        object.__setattr__(
            self,
            "metrics",
            MappingProxyType(dict(self.metrics)),
        )
