"""Contracts for forecast quality scoring, ranking, and model selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping

from ..models import ForecastHorizon


def _validate_unit_interval(name: str, value: float) -> None:
    if not isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class ForecastQualityGrade(str, Enum):
    """Human-readable quality band for a model evidence record."""

    EXCELLENT = "excellent"
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class ForecastQualityProfile:
    """Weights and safeguards used to score model evidence."""

    accuracy_weight: float = 0.35
    calibration_weight: float = 0.25
    directional_weight: float = 0.15
    stability_weight: float = 0.15
    coverage_weight: float = 0.10
    minimum_sample_size: int = 30
    target_sample_size: int = 200
    stale_after_days: int = 180
    minimum_eligible_score: float = 0.50

    def __post_init__(self) -> None:
        weights = (
            self.accuracy_weight,
            self.calibration_weight,
            self.directional_weight,
            self.stability_weight,
            self.coverage_weight,
        )
        for index, weight in enumerate(weights):
            _validate_unit_interval(f"weight[{index}]", weight)
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("Forecast quality weights must sum to 1.0.")
        if self.minimum_sample_size <= 0:
            raise ValueError("minimum_sample_size must be positive.")
        if self.target_sample_size < self.minimum_sample_size:
            raise ValueError(
                "target_sample_size cannot be below minimum_sample_size."
            )
        if self.stale_after_days <= 0:
            raise ValueError("stale_after_days must be positive.")
        _validate_unit_interval(
            "minimum_eligible_score",
            self.minimum_eligible_score,
        )


@dataclass(frozen=True, slots=True)
class ForecastModelEvidence:
    """Historical evidence for one engine, asset class, and horizon."""

    engine_name: str
    engine_version: str
    asset_class: str
    horizon: ForecastHorizon
    evaluation_date: date
    sample_size: int
    accuracy_score: float
    calibration_score: float
    directional_accuracy: float
    stability_score: float
    coverage_score: float
    bias_score: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("engine_name", "engine_version", "asset_class"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required.")
        if self.sample_size < 0:
            raise ValueError("sample_size cannot be negative.")
        for field_name in (
            "accuracy_score",
            "calibration_score",
            "directional_accuracy",
            "stability_score",
            "coverage_score",
        ):
            _validate_unit_interval(field_name, getattr(self, field_name))
        if not isfinite(float(self.bias_score)):
            raise ValueError("bias_score must be finite.")
        if not -1.0 <= self.bias_score <= 1.0:
            raise ValueError("bias_score must be between -1.0 and 1.0.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @property
    def model_key(self) -> tuple[str, str]:
        return (self.engine_name, self.engine_version)


@dataclass(frozen=True, slots=True)
class ForecastQualityScore:
    """Calculated quality score with eligibility and audit details."""

    evidence: ForecastModelEvidence
    raw_score: float
    adjusted_score: float
    sample_factor: float
    freshness_factor: float
    bias_penalty: float
    eligible: bool
    grade: ForecastQualityGrade
    reasons: tuple[str, ...] = ()
    component_scores: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "raw_score",
            "adjusted_score",
            "sample_factor",
            "freshness_factor",
            "bias_penalty",
        ):
            _validate_unit_interval(field_name, getattr(self, field_name))
        object.__setattr__(
            self,
            "component_scores",
            MappingProxyType(dict(self.component_scores)),
        )


@dataclass(frozen=True, slots=True)
class ModelRankingEntry:
    """One ranked model and its supporting quality score."""

    rank: int
    quality: ForecastQualityScore

    def __post_init__(self) -> None:
        if self.rank <= 0:
            raise ValueError("rank must be positive.")

    @property
    def engine_name(self) -> str:
        return self.quality.evidence.engine_name

    @property
    def engine_version(self) -> str:
        return self.quality.evidence.engine_version


@dataclass(frozen=True, slots=True)
class ModelSelectionResult:
    """Auditable model selection decision."""

    asset_class: str
    horizon: ForecastHorizon
    selected: ModelRankingEntry | None
    rankings: tuple[ModelRankingEntry, ...]
    selection_reason: str

    def __post_init__(self) -> None:
        if not self.asset_class.strip():
            raise ValueError("asset_class is required.")
        if self.selected is not None and self.selected not in self.rankings:
            raise ValueError("selected model must be present in rankings.")
