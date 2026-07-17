"""Structured output of universal decision explanation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..contracts.decision_errors import DecisionValidationError


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    """Human-readable and audit-ready explanation of a decision."""

    asset_id: str
    headline: str
    executive_summary: str

    positive_factors: Sequence[str] = field(default_factory=tuple)
    negative_factors: Sequence[str] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)

    eligibility_explanation: str = ""
    scoring_explanation: str = ""
    confidence_explanation: str = ""
    constraint_explanation: str = ""
    allocation_explanation: str = ""

    evidence_references: Sequence[str] = field(default_factory=tuple)
    audit_facts: Mapping[str, Any] = field(default_factory=dict)

    explanation_version: str = "5.1.7"

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise DecisionValidationError(
                "asset_id cannot be empty."
            )

        required_text = {
            "headline": self.headline,
            "executive_summary": self.executive_summary,
            "eligibility_explanation": self.eligibility_explanation,
            "scoring_explanation": self.scoring_explanation,
            "confidence_explanation": self.confidence_explanation,
            "constraint_explanation": self.constraint_explanation,
            "allocation_explanation": self.allocation_explanation,
            "explanation_version": self.explanation_version,
        }

        for name, value in required_text.items():
            if not str(value).strip():
                raise DecisionValidationError(
                    f"{name} cannot be empty."
                )

        for collection_name, values in {
            "positive_factors": self.positive_factors,
            "negative_factors": self.negative_factors,
            "warnings": self.warnings,
            "evidence_references": self.evidence_references,
        }.items():
            if any(not str(value).strip() for value in values):
                raise DecisionValidationError(
                    f"{collection_name} cannot contain blank values."
                )

        for key in self.audit_facts:
            if not str(key).strip():
                raise DecisionValidationError(
                    "audit_facts keys cannot be empty."
                )
