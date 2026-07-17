"""Individual policy checks performed during eligibility evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts.decision_errors import DecisionValidationError
from ..contracts.decision_status import EligibilityStatus


@dataclass(frozen=True, slots=True)
class EligibilityCheck:
    """Result of evaluating one eligibility or data-quality rule."""

    rule_id: str
    passed: bool
    message: str
    actual_value: Any = None
    threshold: Any = None
    failure_status: EligibilityStatus = (
        EligibilityStatus.CONDITIONALLY_ELIGIBLE
    )

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise DecisionValidationError(
                "Eligibility rule_id cannot be empty."
            )

        if not self.message.strip():
            raise DecisionValidationError(
                "Eligibility check message cannot be empty."
            )

        if self.failure_status is EligibilityStatus.ELIGIBLE:
            raise DecisionValidationError(
                "failure_status cannot be ELIGIBLE."
            )
