"""Contracts for forecast performance analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping


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


class PerformanceGrade(str, Enum):
    """Qualitative model-performance grade."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    WEAK = "weak"
    POOR = "poor"


class PerformanceGrouping(str, Enum):
    """Supported scorecard grouping dimensions."""

    OVERALL = "overall"
    MODEL = "model"
    ASSET = "asset"
    HORIZON = "horizon"


@dataclass(frozen=True, slots=True)
class PerformanceAnalyticsProfile:
    """Configuration for performance aggregation and ranking."""

    minimum_sample_size: int = 1
    rolling_window_days: int | None = None
    direction_weight: float = 0.25
    error_weight: float = 0.45
    coverage_weight: float = 0.20
    bias_weight: float = 0.10
    target_interval_coverage: float = 0.95
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.minimum_sample_size <= 0:
            raise ValueError("minimum_sample_size must be positive.")
        if (
            self.rolling_window_days is not None
            and self.rolling_window_days <= 0
        ):
            raise ValueError("rolling_window_days must be positive.")

        weights = (
            self.direction_weight,
            self.error_weight,
            self.coverage_weight,
            self.bias_weight,
        )
        for index, value in enumerate(weights):
            _require_probability(f"weight[{index}]", value)
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("Performance weights must sum to 1.0.")

        _require_probability(
            "target_interval_coverage",
            self.target_interval_coverage,
        )
        if self.target_interval_coverage <= 0:
            raise ValueError(
                "target_interval_coverage must be greater than zero."
            )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ForecastPerformanceMetrics:
    """Aggregated performance metrics for a validation-record group."""

    group_key: str
    grouping: PerformanceGrouping
    sample_size: int
    evaluation_start: date
    evaluation_end: date

    mae: float
    mse: float
    rmse: float
    mape: float | None
    smape: float | None
    mean_bias: float
    mean_relative_bias: float | None
    directional_accuracy: float | None
    interval_coverage: float | None
    interval_coverage_gap: float | None
    scenario_hit_rate: float | None
    score: float
    grade: PerformanceGrade
    eligible: bool
    explanation: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.group_key.strip():
            raise ValueError("group_key is required.")
        if self.sample_size <= 0:
            raise ValueError("sample_size must be positive.")
        if self.evaluation_end < self.evaluation_start:
            raise ValueError(
                "evaluation_end cannot precede evaluation_start."
            )

        for name in (
            "mae",
            "mse",
            "rmse",
            "mean_bias",
            "score",
        ):
            _require_finite(name, getattr(self, name))
        for name in (
            "mape",
            "smape",
            "mean_relative_bias",
            "interval_coverage_gap",
        ):
            _require_finite(name, getattr(self, name))
        for name in (
            "directional_accuracy",
            "interval_coverage",
            "scenario_hit_rate",
            "score",
        ):
            _require_probability(name, getattr(self, name))

        if self.mae < 0 or self.mse < 0 or self.rmse < 0:
            raise ValueError("Error metrics cannot be negative.")
        if self.mape is not None and self.mape < 0:
            raise ValueError("mape cannot be negative.")
        if self.smape is not None and self.smape < 0:
            raise ValueError("smape cannot be negative.")

        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ForecastPerformanceRankingEntry:
    """One ranked performance scorecard."""

    rank: int
    group_key: str
    grouping: PerformanceGrouping
    score: float
    grade: PerformanceGrade
    sample_size: int
    mae: float
    directional_accuracy: float | None
    interval_coverage: float | None
    eligible: bool

    def __post_init__(self) -> None:
        if self.rank <= 0:
            raise ValueError("rank must be positive.")
        if not self.group_key.strip():
            raise ValueError("group_key is required.")
        _require_probability("score", self.score)
        _require_probability(
            "directional_accuracy",
            self.directional_accuracy,
        )
        _require_probability(
            "interval_coverage",
            self.interval_coverage,
        )
        _require_finite("mae", self.mae)
        if self.sample_size <= 0:
            raise ValueError("sample_size must be positive.")


@dataclass(frozen=True, slots=True)
class ForecastPerformanceReport:
    """Performance scorecards and deterministic rankings."""

    generated_for: PerformanceGrouping
    scorecards: tuple[ForecastPerformanceMetrics, ...]
    rankings: tuple[ForecastPerformanceRankingEntry, ...]
    explanation: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.scorecards:
            raise ValueError("At least one scorecard is required.")
        expected = tuple(range(1, len(self.rankings) + 1))
        actual = tuple(item.rank for item in self.rankings)
        if actual != expected:
            raise ValueError("Rankings must be sequential.")
