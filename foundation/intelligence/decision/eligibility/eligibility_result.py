"""Aggregated result of an eligibility and data-quality evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from ..contracts.decision_errors import DecisionValidationError
from ..contracts.decision_status import EligibilityStatus
from .eligibility_check import EligibilityCheck


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    """Auditable eligibility result for one investment opportunity."""

    asset_id: str
    status: EligibilityStatus
    checks: Sequence[EligibilityCheck] = field(default_factory=tuple)
    reasons: Sequence[str] = field(default_factory=tuple)
    policy_id: str = "universal-default"
    policy_version: str = "5.1.2"
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise DecisionValidationError(
                "asset_id cannot be empty."
            )

        if not self.policy_id.strip():
            raise DecisionValidationError(
                "policy_id cannot be empty."
            )

        if not self.policy_version.strip():
            raise DecisionValidationError(
                "policy_version cannot be empty."
            )

        if self.generated_at.tzinfo is None:
            raise DecisionValidationError(
                "generated_at must include timezone information."
            )

    @property
    def passed_checks(self) -> tuple[EligibilityCheck, ...]:
        """Return all checks that passed."""

        return tuple(check for check in self.checks if check.passed)

    @property
    def failed_checks(self) -> tuple[EligibilityCheck, ...]:
        """Return all checks that failed."""

        return tuple(check for check in self.checks if not check.passed)

    @property
    def may_proceed_to_scoring(self) -> bool:
        """Whether the opportunity may continue into decision scoring."""

        return self.status in {
            EligibilityStatus.ELIGIBLE,
            EligibilityStatus.CONDITIONALLY_ELIGIBLE,
        }
