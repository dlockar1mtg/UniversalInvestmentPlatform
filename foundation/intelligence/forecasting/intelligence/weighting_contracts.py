"""Contracts for dynamic ensemble forecast weight optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from ..models import ForecastHorizon
from .calibration_contracts import MarketRegime


def _validate_probability(name: str, value: float) -> None:
    if not isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class WeightOptimizationStatus(str, Enum):
    """Outcome of an ensemble weight optimization request."""

    OPTIMIZED = "optimized"
    FALLBACK_EQUAL = "fallback_equal"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class EnsembleWeightProfile:
    """Weights and constraints used to optimize model contributions."""

    quality_weight: float = 0.35
    calibrated_confidence_weight: float = 0.25
    consensus_alignment_weight: float = 0.20
    reliability_weight: float = 0.15
    regime_match_weight: float = 0.05
    minimum_model_count: int = 2
    minimum_model_weight: float = 0.0
    maximum_model_weight: float = 0.70
    exclude_ineligible_models: bool = True

    def __post_init__(self) -> None:
        weights = (
            self.quality_weight,
            self.calibrated_confidence_weight,
            self.consensus_alignment_weight,
            self.reliability_weight,
            self.regime_match_weight,
        )
        for index, weight in enumerate(weights):
            _validate_probability(f"weight[{index}]", weight)
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("Ensemble weighting factors must sum to 1.0.")
        if self.minimum_model_count < 2:
            raise ValueError("minimum_model_count must be at least 2.")
        _validate_probability(
            "minimum_model_weight",
            self.minimum_model_weight,
        )
        _validate_probability(
            "maximum_model_weight",
            self.maximum_model_weight,
        )
        if self.minimum_model_weight > self.maximum_model_weight:
            raise ValueError(
                "minimum_model_weight cannot exceed maximum_model_weight."
            )


@dataclass(frozen=True, slots=True)
class EnsembleModelSignal:
    """Comparable evidence used to assign one model's ensemble weight."""

    engine_name: str
    engine_version: str
    asset_class: str
    horizon: ForecastHorizon
    regime: MarketRegime
    model_quality_score: float
    calibrated_confidence: float
    consensus_alignment_score: float
    reliability_score: float
    regime_match_score: float
    eligible: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "engine_name",
            "engine_version",
            "asset_class",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required.")
        for field_name in (
            "model_quality_score",
            "calibrated_confidence",
            "consensus_alignment_score",
            "reliability_score",
            "regime_match_score",
        ):
            _validate_probability(field_name, getattr(self, field_name))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @property
    def model_key(self) -> tuple[str, str]:
        return (self.engine_name, self.engine_version)


@dataclass(frozen=True, slots=True)
class EnsembleWeightEntry:
    """Final normalized weight and audit details for one model."""

    engine_name: str
    engine_version: str
    raw_score: float
    normalized_weight: float
    constrained_weight: float
    eligible: bool
    factors: Mapping[str, float] = field(default_factory=dict)
    explanation: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.engine_name.strip() or not self.engine_version.strip():
            raise ValueError("Engine name and version are required.")
        if self.raw_score < 0 or not isfinite(float(self.raw_score)):
            raise ValueError("raw_score must be finite and non-negative.")
        _validate_probability(
            "normalized_weight",
            self.normalized_weight,
        )
        _validate_probability(
            "constrained_weight",
            self.constrained_weight,
        )
        object.__setattr__(
            self,
            "factors",
            MappingProxyType(dict(self.factors)),
        )

    @property
    def model_key(self) -> tuple[str, str]:
        return (self.engine_name, self.engine_version)


@dataclass(frozen=True, slots=True)
class EnsembleWeightResult:
    """Auditable output from ensemble weight optimization."""

    asset_class: str
    horizon: ForecastHorizon
    regime: MarketRegime
    status: WeightOptimizationStatus
    weights: tuple[EnsembleWeightEntry, ...]
    eligible_model_count: int
    excluded_model_count: int
    explanation: tuple[str, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.asset_class.strip():
            raise ValueError("asset_class is required.")
        if self.eligible_model_count < 0 or self.excluded_model_count < 0:
            raise ValueError("Model counts cannot be negative.")
        if self.weights:
            total = sum(item.constrained_weight for item in self.weights)
            if abs(total - 1.0) > 1e-9:
                raise ValueError(
                    "Constrained ensemble weights must sum to 1.0."
                )
        object.__setattr__(self, "metrics", _freeze_mapping(self.metrics))
