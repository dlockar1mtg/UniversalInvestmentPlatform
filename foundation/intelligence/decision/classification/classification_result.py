"""Auditable result of universal action classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from ..contracts.decision_action import DecisionAction
from ..contracts.decision_errors import DecisionValidationError
from ..contracts.decision_status import EligibilityStatus


@dataclass(frozen=True, slots=True)
class ActionClassificationResult:
    """Action assigned from eligibility, score, and position context."""

    asset_id: str
    action: DecisionAction
    eligibility: EligibilityStatus
    final_score: float
    position_exists: bool
    reasons: Sequence[str] = field(default_factory=tuple)
    classification_version: str = "5.1.4"

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise DecisionValidationError(
                "asset_id cannot be empty."
            )

        if not 0.0 <= float(self.final_score) <= 100.0:
            raise DecisionValidationError(
                "final_score must be between 0.0 and 100.0."
            )

        if not self.classification_version.strip():
            raise DecisionValidationError(
                "classification_version cannot be empty."
            )

        if not self.reasons:
            raise DecisionValidationError(
                "At least one classification reason is required."
            )

        if any(not str(reason).strip() for reason in self.reasons):
            raise DecisionValidationError(
                "Classification reasons cannot be blank."
            )
