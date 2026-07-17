"""Auditable portfolio and policy constraint results."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Sequence

from ..contracts.decision_errors import DecisionValidationError
from .constraint_status import ConstraintStatus


@dataclass(frozen=True, slots=True)
class ConstraintCheck:
    """Result of one portfolio, policy, or execution constraint."""

    constraint_id: str
    status: ConstraintStatus
    message: str
    actual_value: Any = None
    limit_value: Any = None
    allocation_limit: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.constraint_id.strip():
            raise DecisionValidationError(
                "constraint_id cannot be empty."
            )

        if not self.message.strip():
            raise DecisionValidationError(
                "Constraint message cannot be empty."
            )

        if (
            self.allocation_limit is not None
            and self.allocation_limit < Decimal("0")
        ):
            raise DecisionValidationError(
                "allocation_limit cannot be negative."
            )


@dataclass(frozen=True, slots=True)
class ConstraintEvaluationResult:
    """Aggregated constraint evaluation for one opportunity."""

    asset_id: str
    status: ConstraintStatus
    checks: Sequence[ConstraintCheck] = field(default_factory=tuple)
    maximum_permitted_allocation: Decimal = Decimal("0")
    binding_constraint: str | None = None
    reasons: Sequence[str] = field(default_factory=tuple)
    constraint_version: str = "5.1.6"

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise DecisionValidationError(
                "asset_id cannot be empty."
            )

        if self.maximum_permitted_allocation < Decimal("0"):
            raise DecisionValidationError(
                "maximum_permitted_allocation cannot be negative."
            )

        if not self.constraint_version.strip():
            raise DecisionValidationError(
                "constraint_version cannot be empty."
            )

        if not self.reasons:
            raise DecisionValidationError(
                "At least one constraint reason is required."
            )

    @property
    def blocked_checks(self) -> tuple[ConstraintCheck, ...]:
        """Return all hard-blocking constraints."""

        return tuple(
            check
            for check in self.checks
            if check.status is ConstraintStatus.BLOCKED
        )

    @property
    def warning_checks(self) -> tuple[ConstraintCheck, ...]:
        """Return all warning-level constraints."""

        return tuple(
            check
            for check in self.checks
            if check.status is ConstraintStatus.WARNING
        )

    @property
    def may_allocate(self) -> bool:
        """Whether additional capital may be allocated."""

        return (
            self.status is not ConstraintStatus.BLOCKED
            and self.maximum_permitted_allocation > Decimal("0")
        )
