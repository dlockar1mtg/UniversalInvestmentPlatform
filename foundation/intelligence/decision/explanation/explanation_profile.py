"""Configuration for universal decision explanations."""

from __future__ import annotations

from dataclasses import dataclass

from .explanation_errors import ExplanationConfigurationError


@dataclass(frozen=True, slots=True)
class ExplanationProfile:
    """Formatting and selection rules for decision explanations."""

    profile_id: str = "universal-explanation-default"
    explanation_version: str = "5.1.7"

    maximum_positive_factors: int = 3
    maximum_negative_factors: int = 5
    maximum_warnings: int = 5
    maximum_evidence_references: int = 10

    include_audit_facts: bool = True
    include_all_policy_violations: bool = True

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ExplanationConfigurationError(
                "profile_id cannot be empty."
            )

        if not self.explanation_version.strip():
            raise ExplanationConfigurationError(
                "explanation_version cannot be empty."
            )

        count_fields = {
            "maximum_positive_factors": self.maximum_positive_factors,
            "maximum_negative_factors": self.maximum_negative_factors,
            "maximum_warnings": self.maximum_warnings,
            "maximum_evidence_references": (
                self.maximum_evidence_references
            ),
        }

        for name, value in count_fields.items():
            if value < 0:
                raise ExplanationConfigurationError(
                    f"{name} cannot be negative."
                )
