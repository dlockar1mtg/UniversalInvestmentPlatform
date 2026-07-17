"""Contracts for forecast certification and production readiness."""

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


class CertificationStatus(str, Enum):
    """Forecast model certification outcome."""

    CERTIFIED = "certified"
    CONDITIONAL = "conditional"
    REJECTED = "rejected"
    PENDING = "pending"


class CertificationGate(str, Enum):
    """Named production-readiness gate."""

    SAMPLE_SIZE = "sample_size"
    PERFORMANCE = "performance"
    DIRECTION = "direction"
    CALIBRATION = "calibration"
    REPUTATION = "reputation"
    DRIFT = "drift"
    ELIGIBILITY = "eligibility"


@dataclass(frozen=True, slots=True)
class ForecastCertificationProfile:
    """Thresholds used for production certification."""

    minimum_sample_size: int = 10
    minimum_performance_score: float = 0.70
    minimum_directional_accuracy: float = 0.55
    maximum_interval_coverage_gap: float = 0.15
    minimum_reputation: float = 0.60
    maximum_drift_score: float = 0.40
    conditional_margin: float = 0.10
    validity_days: int = 90
    require_interval_coverage: bool = True
    require_directional_accuracy: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.minimum_sample_size <= 0:
            raise ValueError("minimum_sample_size must be positive.")
        for name in (
            "minimum_performance_score",
            "minimum_directional_accuracy",
            "maximum_interval_coverage_gap",
            "minimum_reputation",
            "maximum_drift_score",
            "conditional_margin",
        ):
            _require_probability(name, getattr(self, name))
        if self.validity_days <= 0:
            raise ValueError("validity_days must be positive.")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class CertificationGateResult:
    """Result of one certification gate."""

    gate: CertificationGate
    passed: bool
    conditional: bool
    observed_value: float | int | bool | None
    required_value: float | int | bool | None
    explanation: str

    def __post_init__(self) -> None:
        if self.passed and self.conditional:
            raise ValueError(
                "A gate cannot be both passed and conditional."
            )
        if not self.explanation.strip():
            raise ValueError("explanation is required.")
        if isinstance(self.observed_value, float):
            _require_finite("observed_value", self.observed_value)
        if isinstance(self.required_value, float):
            _require_finite("required_value", self.required_value)


@dataclass(frozen=True, slots=True)
class ForecastCertificationRecord:
    """Immutable certification decision for one model."""

    certification_id: str
    model_key: str
    status: CertificationStatus
    certified_at: datetime
    effective_date: date
    expires_on: date
    gates: tuple[CertificationGateResult, ...]
    score: float
    reasons: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.certification_id.strip():
            raise ValueError("certification_id is required.")
        if not self.model_key.strip():
            raise ValueError("model_key is required.")
        if self.certified_at.tzinfo is None:
            raise ValueError("certified_at must be timezone-aware.")
        if self.expires_on < self.effective_date:
            raise ValueError(
                "expires_on cannot precede effective_date."
            )
        if not self.gates:
            raise ValueError("At least one certification gate is required.")
        _require_probability("score", self.score)
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @property
    def is_active(self) -> bool:
        return (
            self.status in (
                CertificationStatus.CERTIFIED,
                CertificationStatus.CONDITIONAL,
            )
            and self.effective_date <= date.today() <= self.expires_on
        )


@dataclass(frozen=True, slots=True)
class ForecastCertificationReport:
    """Certification results for one or more models."""

    records: tuple[ForecastCertificationRecord, ...]
    generated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")
        if not self.records:
            raise ValueError("At least one certification record is required.")
        keys = [item.model_key for item in self.records]
        if len(keys) != len(set(keys)):
            raise ValueError(
                "Certification report model keys must be unique."
            )
