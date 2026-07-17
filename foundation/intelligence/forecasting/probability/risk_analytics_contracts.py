"""Contracts for forecast-distribution risk analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _require_finite(name: str, value: float) -> None:
    if not isfinite(float(value)):
        raise ValueError(f"{name} must be finite.")


def _require_probability(name: str, value: float) -> None:
    _require_finite(name, value)
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0.")


class DistributionRiskGrade(str, Enum):
    """Qualitative risk grade derived from a distribution."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass(frozen=True, slots=True)
class DistributionRiskProfile:
    """Configuration for shared distribution-risk analytics."""

    var_confidence_levels: tuple[float, ...] = (0.90, 0.95, 0.99)
    uncertainty_interval_coverage: float = 0.90
    downside_target_return: float = 0.0
    upside_target_return: float = 0.10
    risk_free_rate: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.var_confidence_levels) != len(
            set(self.var_confidence_levels)
        ):
            raise ValueError(
                "var_confidence_levels must be unique."
            )
        for level in self.var_confidence_levels:
            _require_probability(
                "var_confidence_levels[]",
                level,
            )
            if level <= 0.5:
                raise ValueError(
                    "VaR confidence levels must exceed 0.5."
                )
        _require_probability(
            "uncertainty_interval_coverage",
            self.uncertainty_interval_coverage,
        )
        if not 0.0 < self.uncertainty_interval_coverage < 1.0:
            raise ValueError(
                "uncertainty_interval_coverage must be between "
                "zero and one."
            )
        for name in (
            "downside_target_return",
            "upside_target_return",
            "risk_free_rate",
        ):
            _require_finite(name, getattr(self, name))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class TailRiskPoint:
    """VaR and Expected Shortfall at one confidence level."""

    confidence_level: float
    value_at_risk: float
    expected_shortfall: float

    def __post_init__(self) -> None:
        _require_probability("confidence_level", self.confidence_level)
        if self.confidence_level <= 0.5:
            raise ValueError(
                "confidence_level must be greater than 0.5."
            )
        _require_finite("value_at_risk", self.value_at_risk)
        _require_finite(
            "expected_shortfall",
            self.expected_shortfall,
        )
        if self.expected_shortfall > self.value_at_risk + 1e-12:
            raise ValueError(
                "expected_shortfall cannot exceed value_at_risk."
            )


@dataclass(frozen=True, slots=True)
class DistributionRiskMetrics:
    """Risk summary derived from one forecast distribution."""

    asset_id: str
    distribution_id: str
    expected_return: float
    median_return: float
    volatility: float
    downside_probability: float
    upside_probability: float
    probability_of_loss: float
    target_attainment_probability: float | None
    downside_deviation: float
    upside_potential: float
    interval_width: float
    normalized_interval_width: float
    asymmetry_score: float
    tail_concentration: float
    risk_adjusted_return: float
    tail_risk: tuple[TailRiskPoint, ...]
    risk_score: float
    risk_grade: DistributionRiskGrade
    explanation: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.asset_id.strip() or not self.distribution_id.strip():
            raise ValueError(
                "asset_id and distribution_id are required."
            )
        for name in (
            "expected_return",
            "median_return",
            "volatility",
            "downside_probability",
            "upside_probability",
            "probability_of_loss",
            "downside_deviation",
            "upside_potential",
            "interval_width",
            "normalized_interval_width",
            "asymmetry_score",
            "tail_concentration",
            "risk_adjusted_return",
            "risk_score",
        ):
            _require_finite(name, getattr(self, name))
        for name in (
            "downside_probability",
            "upside_probability",
            "probability_of_loss",
            "tail_concentration",
            "risk_score",
        ):
            _require_probability(name, getattr(self, name))
        if self.target_attainment_probability is not None:
            _require_probability(
                "target_attainment_probability",
                self.target_attainment_probability,
            )
        if self.volatility < 0:
            raise ValueError("volatility cannot be negative.")
        if self.downside_deviation < 0:
            raise ValueError(
                "downside_deviation cannot be negative."
            )
        if self.upside_potential < 0:
            raise ValueError(
                "upside_potential cannot be negative."
            )
        if self.interval_width < 0:
            raise ValueError("interval_width cannot be negative.")
        if self.normalized_interval_width < 0:
            raise ValueError(
                "normalized_interval_width cannot be negative."
            )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class DistributionComparisonEntry:
    """One distribution's relative risk ranking."""

    rank: int
    asset_id: str
    distribution_id: str
    risk_score: float
    risk_grade: DistributionRiskGrade
    risk_adjusted_return: float
    expected_return: float
    probability_of_loss: float

    def __post_init__(self) -> None:
        if self.rank <= 0:
            raise ValueError("rank must be positive.")
        _require_probability("risk_score", self.risk_score)
        _require_probability(
            "probability_of_loss",
            self.probability_of_loss,
        )
        for name in (
            "risk_adjusted_return",
            "expected_return",
        ):
            _require_finite(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class DistributionComparisonResult:
    """Deterministic ranking across multiple forecast distributions."""

    entries: tuple[DistributionComparisonEntry, ...]
    explanation: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError(
                "At least one comparison entry is required."
            )
        expected_ranks = tuple(range(1, len(self.entries) + 1))
        actual_ranks = tuple(item.rank for item in self.entries)
        if actual_ranks != expected_ranks:
            raise ValueError(
                "Comparison ranks must be sequential."
            )
