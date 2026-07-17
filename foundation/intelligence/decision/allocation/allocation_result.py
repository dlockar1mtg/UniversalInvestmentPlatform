"""Auditable single-opportunity allocation recommendation."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping, Sequence

from ..contracts.decision_action import DecisionAction
from ..contracts.decision_errors import DecisionValidationError


@dataclass(frozen=True, slots=True)
class AllocationResult:
    """Capital recommendation for one investment decision."""

    asset_id: str
    action: DecisionAction
    requested_allocation: Decimal
    maximum_allocation: Decimal
    recommended_allocation: Decimal
    allocation_percentage: float
    binding_constraint: str | None

    sizing_factors: Mapping[str, float] = field(default_factory=dict)
    reasons: Sequence[str] = field(default_factory=tuple)
    allocation_version: str = "5.1.6"

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise DecisionValidationError(
                "asset_id cannot be empty."
            )

        for name, value in {
            "requested_allocation": self.requested_allocation,
            "maximum_allocation": self.maximum_allocation,
            "recommended_allocation": self.recommended_allocation,
        }.items():
            if value < Decimal("0"):
                raise DecisionValidationError(
                    f"{name} cannot be negative."
                )

        if self.recommended_allocation > self.maximum_allocation:
            raise DecisionValidationError(
                "recommended_allocation cannot exceed "
                "maximum_allocation."
            )

        if not 0.0 <= float(self.allocation_percentage) <= 1.0:
            raise DecisionValidationError(
                "allocation_percentage must be between 0.0 and 1.0."
            )

        for name, value in self.sizing_factors.items():
            if not str(name).strip():
                raise DecisionValidationError(
                    "Sizing factor names cannot be empty."
                )

            if not 0.0 <= float(value) <= 1.0:
                raise DecisionValidationError(
                    f"Sizing factor {name!r} must be between 0.0 and 1.0."
                )

        if not self.reasons:
            raise DecisionValidationError(
                "At least one allocation reason is required."
            )

        if not self.allocation_version.strip():
            raise DecisionValidationError(
                "allocation_version cannot be empty."
            )
