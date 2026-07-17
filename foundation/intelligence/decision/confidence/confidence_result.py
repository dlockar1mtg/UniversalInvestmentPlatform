"""Auditable output of confidence aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from ..contracts.decision_errors import DecisionValidationError
from .confidence_band import ConfidenceBand


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    """Structured confidence result for an investment recommendation."""

    asset_id: str
    raw_confidence: float
    adjustment_score: float
    final_confidence: float
    confidence_band: ConfidenceBand

    component_scores: Mapping[str, float] = field(default_factory=dict)
    adjustments: Mapping[str, float] = field(default_factory=dict)
    reasons: Sequence[str] = field(default_factory=tuple)
    confidence_version: str = "5.1.5"

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise DecisionValidationError(
                "asset_id cannot be empty."
            )

        for name, value in {
            "raw_confidence": self.raw_confidence,
            "final_confidence": self.final_confidence,
        }.items():
            if not 0.0 <= float(value) <= 1.0:
                raise DecisionValidationError(
                    f"{name} must be between 0.0 and 1.0."
                )

        if not 0.0 <= float(self.adjustment_score) <= 100.0:
            raise DecisionValidationError(
                "adjustment_score must be between 0.0 and 100.0."
            )

        for name, value in self.component_scores.items():
            if not str(name).strip():
                raise DecisionValidationError(
                    "Confidence component names cannot be empty."
                )

            if not 0.0 <= float(value) <= 100.0:
                raise DecisionValidationError(
                    f"Confidence component {name!r} must be "
                    "between 0.0 and 100.0."
                )

        for name, value in self.adjustments.items():
            if not str(name).strip():
                raise DecisionValidationError(
                    "Confidence adjustment names cannot be empty."
                )

            if not 0.0 <= float(value) <= 100.0:
                raise DecisionValidationError(
                    f"Confidence adjustment {name!r} must be "
                    "between 0.0 and 100.0."
                )

        if not self.reasons:
            raise DecisionValidationError(
                "At least one confidence reason is required."
            )

        if any(not str(reason).strip() for reason in self.reasons):
            raise DecisionValidationError(
                "Confidence reasons cannot be blank."
            )

        if not self.confidence_version.strip():
            raise DecisionValidationError(
                "confidence_version cannot be empty."
            )
