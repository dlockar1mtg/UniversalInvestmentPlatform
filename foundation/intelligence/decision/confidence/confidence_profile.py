"""Configuration profiles for universal confidence aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose
from typing import Mapping

from .confidence_errors import ConfidenceConfigurationError


DEFAULT_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "forecast_confidence": 0.25,
    "historical_reliability": 0.25,
    "data_quality": 0.20,
    "evidence_quality": 0.15,
    "evidence_consistency": 0.10,
    "eligibility_quality": 0.05,
}


@dataclass(frozen=True, slots=True)
class ConfidenceProfile:
    """Weights, adjustments, and bands for confidence aggregation."""

    profile_id: str = "universal-confidence-default"
    confidence_version: str = "5.1.5"

    component_weights: Mapping[str, float] = field(
        default_factory=lambda: dict(DEFAULT_CONFIDENCE_WEIGHTS)
    )

    conditional_eligibility_adjustment: float = 5.0
    partial_evidence_freshness_adjustment: float = 5.0
    maximum_limited_evidence_adjustment: float = 10.0
    maximum_model_disagreement_adjustment: float = 10.0
    maximum_unsupported_assumption_adjustment: float = 8.0
    maximum_regime_instability_adjustment: float = 7.0

    very_high_threshold: float = 0.85
    high_threshold: float = 0.70
    moderate_threshold: float = 0.55
    low_threshold: float = 0.40

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ConfidenceConfigurationError(
                "profile_id cannot be empty."
            )

        if not self.confidence_version.strip():
            raise ConfidenceConfigurationError(
                "confidence_version cannot be empty."
            )

        expected = set(DEFAULT_CONFIDENCE_WEIGHTS)
        actual = set(self.component_weights)

        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)

            raise ConfidenceConfigurationError(
                "component_weights must contain exactly the universal "
                f"confidence components. Missing={missing}; "
                f"unexpected={unexpected}."
            )

        for name, weight in self.component_weights.items():
            if not 0.0 <= float(weight) <= 1.0:
                raise ConfidenceConfigurationError(
                    f"Weight {name!r} must be between 0.0 and 1.0."
                )

        if not isclose(
            sum(self.component_weights.values()),
            1.0,
            abs_tol=1e-9,
        ):
            raise ConfidenceConfigurationError(
                "Confidence component weights must sum to 1.0."
            )

        adjustments = {
            "conditional_eligibility_adjustment": (
                self.conditional_eligibility_adjustment
            ),
            "partial_evidence_freshness_adjustment": (
                self.partial_evidence_freshness_adjustment
            ),
            "maximum_limited_evidence_adjustment": (
                self.maximum_limited_evidence_adjustment
            ),
            "maximum_model_disagreement_adjustment": (
                self.maximum_model_disagreement_adjustment
            ),
            "maximum_unsupported_assumption_adjustment": (
                self.maximum_unsupported_assumption_adjustment
            ),
            "maximum_regime_instability_adjustment": (
                self.maximum_regime_instability_adjustment
            ),
        }

        for name, value in adjustments.items():
            if not 0.0 <= float(value) <= 100.0:
                raise ConfidenceConfigurationError(
                    f"{name} must be between 0.0 and 100.0."
                )

        thresholds = (
            self.very_high_threshold,
            self.high_threshold,
            self.moderate_threshold,
            self.low_threshold,
        )

        for value in thresholds:
            if not 0.0 <= float(value) <= 1.0:
                raise ConfidenceConfigurationError(
                    "Confidence thresholds must be between 0.0 and 1.0."
                )

        if list(thresholds) != sorted(thresholds, reverse=True):
            raise ConfidenceConfigurationError(
                "Confidence thresholds must be ordered highest to lowest."
            )
