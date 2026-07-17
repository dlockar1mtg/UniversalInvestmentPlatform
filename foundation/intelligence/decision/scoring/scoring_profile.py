"""Configuration profiles for universal decision scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose
from typing import Mapping

from .scoring_errors import ScoringConfigurationError


DEFAULT_COMPONENT_WEIGHTS: dict[str, float] = {
    "forecast_strength": 0.20,
    "forecast_confidence": 0.15,
    "historical_reliability": 0.15,
    "risk_adjusted_opportunity": 0.15,
    "market_regime_alignment": 0.10,
    "diversification_fit": 0.10,
    "liquidity_quality": 0.05,
    "valuation_attractiveness": 0.10,
}


@dataclass(frozen=True, slots=True)
class DecisionScoringProfile:
    """Weights and penalty limits used by the scoring engine."""

    profile_id: str = "universal-balanced"
    scoring_version: str = "5.1.3"

    component_weights: Mapping[str, float] = field(
        default_factory=lambda: dict(DEFAULT_COMPONENT_WEIGHTS)
    )

    maximum_data_quality_penalty: float = 8.0
    conditional_eligibility_penalty: float = 4.0
    maximum_asset_concentration_penalty: float = 6.0
    maximum_asset_class_concentration_penalty: float = 6.0
    partial_evidence_freshness_penalty: float = 3.0
    maximum_evidence_conflict_penalty: float = 8.0

    concentration_warning_ratio: float = 0.75

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ScoringConfigurationError(
                "profile_id cannot be empty."
            )

        if not self.scoring_version.strip():
            raise ScoringConfigurationError(
                "scoring_version cannot be empty."
            )

        expected_components = set(DEFAULT_COMPONENT_WEIGHTS)
        actual_components = set(self.component_weights)

        if actual_components != expected_components:
            missing = sorted(expected_components - actual_components)
            unexpected = sorted(actual_components - expected_components)

            raise ScoringConfigurationError(
                "component_weights must contain exactly the universal "
                f"scoring components. Missing={missing}; "
                f"unexpected={unexpected}."
            )

        for name, weight in self.component_weights.items():
            if not 0.0 <= float(weight) <= 1.0:
                raise ScoringConfigurationError(
                    f"Weight {name!r} must be between 0.0 and 1.0."
                )

        if not isclose(
            sum(self.component_weights.values()),
            1.0,
            abs_tol=1e-9,
        ):
            raise ScoringConfigurationError(
                "Universal component weights must sum to 1.0."
            )

        penalty_fields = {
            "maximum_data_quality_penalty": (
                self.maximum_data_quality_penalty
            ),
            "conditional_eligibility_penalty": (
                self.conditional_eligibility_penalty
            ),
            "maximum_asset_concentration_penalty": (
                self.maximum_asset_concentration_penalty
            ),
            "maximum_asset_class_concentration_penalty": (
                self.maximum_asset_class_concentration_penalty
            ),
            "partial_evidence_freshness_penalty": (
                self.partial_evidence_freshness_penalty
            ),
            "maximum_evidence_conflict_penalty": (
                self.maximum_evidence_conflict_penalty
            ),
        }

        for name, value in penalty_fields.items():
            if not 0.0 <= float(value) <= 100.0:
                raise ScoringConfigurationError(
                    f"{name} must be between 0.0 and 100.0."
                )

        if not 0.0 <= self.concentration_warning_ratio <= 1.0:
            raise ScoringConfigurationError(
                "concentration_warning_ratio must be between 0.0 and 1.0."
            )
