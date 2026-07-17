"""Output contract produced by the Universal Decision Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence

from .decision_action import DecisionAction
from .decision_errors import DecisionValidationError
from .decision_evidence import DecisionEvidence
from .decision_score import DecisionScore
from .decision_status import DecisionStatus, EligibilityStatus


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """Auditable result of evaluating one investment opportunity."""

    decision_id: str
    asset_id: str
    asset_class: str
    action: DecisionAction
    status: DecisionStatus
    eligibility: EligibilityStatus
    score: DecisionScore
    confidence: float

    maximum_allocation: Decimal = Decimal("0")
    recommended_allocation: Decimal = Decimal("0")

    reasons: Sequence[str] = field(default_factory=tuple)
    evidence: Sequence[DecisionEvidence] = field(default_factory=tuple)
    policy_violations: Sequence[str] = field(default_factory=tuple)

    policy_id: str = "universal-default"
    policy_version: str = "5.1.2"
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise DecisionValidationError(
                "decision_id cannot be empty."
            )

        if not self.asset_id.strip():
            raise DecisionValidationError("asset_id cannot be empty.")

        if not self.asset_class.strip():
            raise DecisionValidationError(
                "asset_class cannot be empty."
            )

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise DecisionValidationError(
                "confidence must be between 0.0 and 1.0."
            )

        if self.maximum_allocation < Decimal("0"):
            raise DecisionValidationError(
                "maximum_allocation cannot be negative."
            )

        if self.recommended_allocation < Decimal("0"):
            raise DecisionValidationError(
                "recommended_allocation cannot be negative."
            )

        if self.recommended_allocation > self.maximum_allocation:
            raise DecisionValidationError(
                "recommended_allocation cannot exceed "
                "maximum_allocation."
            )

        if not self.policy_id.strip():
            raise DecisionValidationError("policy_id cannot be empty.")

        if not self.policy_version.strip():
            raise DecisionValidationError(
                "policy_version cannot be empty."
            )

        if self.generated_at.tzinfo is None:
            raise DecisionValidationError(
                "generated_at must include timezone information."
            )

        if self.expires_at is not None:
            if self.expires_at.tzinfo is None:
                raise DecisionValidationError(
                    "expires_at must include timezone information."
                )

            if self.expires_at <= self.generated_at:
                raise DecisionValidationError(
                    "expires_at must occur after generated_at."
                )
