"""Contracts for continuous forecast learning."""

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


class ModelLearningStatus(str, Enum):
    """Adaptive model lifecycle state."""

    PROMOTED = "promoted"
    STABLE = "stable"
    WATCH = "watch"
    DEMOTED = "demoted"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True, slots=True)
class ContinuousLearningProfile:
    """Configuration for model reputation and adaptive weights."""

    baseline_reputation: float = 0.50
    performance_weight: float = 0.65
    recency_weight: float = 0.20
    stability_weight: float = 0.15
    minimum_sample_size: int = 3
    promotion_threshold: float = 0.80
    demotion_threshold: float = 0.40
    watch_threshold: float = 0.55
    recency_half_life_days: int = 180
    maximum_weight_change: float = 0.15
    minimum_model_weight: float = 0.0
    maximum_model_weight: float = 0.70
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "baseline_reputation",
            "performance_weight",
            "recency_weight",
            "stability_weight",
            "promotion_threshold",
            "demotion_threshold",
            "watch_threshold",
            "maximum_weight_change",
            "minimum_model_weight",
            "maximum_model_weight",
        ):
            _require_probability(name, getattr(self, name))

        if abs(
            self.performance_weight
            + self.recency_weight
            + self.stability_weight
            - 1.0
        ) > 1e-9:
            raise ValueError("Learning factor weights must sum to 1.0.")

        if self.minimum_sample_size <= 0:
            raise ValueError("minimum_sample_size must be positive.")
        if self.recency_half_life_days <= 0:
            raise ValueError("recency_half_life_days must be positive.")
        if self.demotion_threshold > self.watch_threshold:
            raise ValueError(
                "demotion_threshold cannot exceed watch_threshold."
            )
        if self.watch_threshold > self.promotion_threshold:
            raise ValueError(
                "watch_threshold cannot exceed promotion_threshold."
            )
        if self.minimum_model_weight > self.maximum_model_weight:
            raise ValueError(
                "minimum_model_weight cannot exceed maximum_model_weight."
            )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ModelLearningSignal:
    """One model's continuous-learning signal."""

    model_key: str
    as_of_date: date
    sample_size: int
    performance_score: float
    prior_reputation: float
    recency_score: float
    stability_score: float
    new_reputation: float
    reputation_change: float
    status: ModelLearningStatus
    current_weight: float
    recommended_weight: float
    weight_change: float
    explanation: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_key.strip():
            raise ValueError("model_key is required.")
        if self.sample_size <= 0:
            raise ValueError("sample_size must be positive.")
        for name in (
            "performance_score",
            "prior_reputation",
            "recency_score",
            "stability_score",
            "new_reputation",
            "current_weight",
            "recommended_weight",
        ):
            _require_probability(name, getattr(self, name))
        for name in ("reputation_change", "weight_change"):
            _require_finite(name, getattr(self, name))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ModelLearningSnapshot:
    """Persistent adaptive state for one model."""

    model_key: str
    reputation: float
    adaptive_weight: float
    status: ModelLearningStatus
    sample_size: int
    updated_at: datetime = field(default_factory=_utc_now)
    update_count: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_key.strip():
            raise ValueError("model_key is required.")
        _require_probability("reputation", self.reputation)
        _require_probability("adaptive_weight", self.adaptive_weight)
        if self.sample_size <= 0:
            raise ValueError("sample_size must be positive.")
        if self.update_count <= 0:
            raise ValueError("update_count must be positive.")
        if self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class LearningState:
    """Immutable collection of model learning snapshots."""

    snapshots: tuple[ModelLearningSnapshot, ...]
    generated_at: datetime = field(default_factory=_utc_now)
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")
        keys = [item.model_key for item in self.snapshots]
        if len(keys) != len(set(keys)):
            raise ValueError("Learning state model keys must be unique.")

    def get(self, model_key: str) -> ModelLearningSnapshot | None:
        for item in self.snapshots:
            if item.model_key == model_key:
                return item
        return None


@dataclass(frozen=True, slots=True)
class ContinuousLearningResult:
    """Signals and updated persistent learning state."""

    signals: tuple[ModelLearningSignal, ...]
    state: LearningState

    def __post_init__(self) -> None:
        signal_keys = {item.model_key for item in self.signals}
        state_keys = {item.model_key for item in self.state.snapshots}
        if signal_keys != state_keys:
            raise ValueError(
                "Continuous-learning signals and state keys must match."
            )
