"""Metric-level score component contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .score_dimension import ScoreDimension
from .validation import (
    to_decimal,
    validate_non_empty_text,
    validate_score,
    validate_unit_interval,
)


class DataAvailability(str, Enum):
    """Explicit data state for a metric used by the scoring engine."""

    AVAILABLE = "available"
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"
    STALE = "stale"
    INSUFFICIENT_HISTORY = "insufficient_history"


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    """One raw metric and its normalized scoring metadata."""

    metric_name: str
    dimension: ScoreDimension
    availability: DataAvailability
    raw_value: Decimal | None
    normalized_score: Decimal | None
    weight: Decimal
    confidence: Decimal
    source: str
    calculation_method: str
    warning: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metric_name",
            validate_non_empty_text(self.metric_name, "metric_name"),
        )
        object.__setattr__(self, "weight", validate_unit_interval(self.weight, "weight"))
        object.__setattr__(
            self,
            "confidence",
            validate_unit_interval(self.confidence, "confidence"),
        )
        object.__setattr__(self, "source", validate_non_empty_text(self.source, "source"))
        object.__setattr__(
            self,
            "calculation_method",
            validate_non_empty_text(self.calculation_method, "calculation_method"),
        )

        if self.raw_value is not None:
            object.__setattr__(self, "raw_value", to_decimal(self.raw_value, "raw_value"))

        if self.availability is DataAvailability.AVAILABLE:
            if self.normalized_score is None:
                raise ValueError("Available components require normalized_score.")
            object.__setattr__(
                self,
                "normalized_score",
                validate_score(self.normalized_score, "normalized_score"),
            )
        elif self.normalized_score is not None:
            raise ValueError(
                "Unavailable components must not contain normalized_score."
            )

        if self.warning is not None:
            object.__setattr__(
                self,
                "warning",
                validate_non_empty_text(self.warning, "warning"),
            )
