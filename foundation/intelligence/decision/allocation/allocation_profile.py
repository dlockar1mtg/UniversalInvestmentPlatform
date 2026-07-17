"""Configuration for single-decision capital allocation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .allocation_errors import AllocationConfigurationError


@dataclass(frozen=True, slots=True)
class AllocationProfile:
    """Sizing rules for one classified investment opportunity."""

    profile_id: str = "universal-single-decision"
    allocation_version: str = "5.1.6"

    strong_buy_multiplier: float = 1.00
    buy_multiplier: float = 0.75
    accumulate_multiplier: float = 0.50

    minimum_confidence_multiplier: float = 0.25
    conditional_eligibility_multiplier: float = 0.50

    maximum_single_decision_fraction: float = 1.00
    minimum_recommended_allocation: Decimal = Decimal("0")
    rounding_increment: Decimal = Decimal("0.01")

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise AllocationConfigurationError(
                "profile_id cannot be empty."
            )

        if not self.allocation_version.strip():
            raise AllocationConfigurationError(
                "allocation_version cannot be empty."
            )

        ratio_fields = {
            "strong_buy_multiplier": self.strong_buy_multiplier,
            "buy_multiplier": self.buy_multiplier,
            "accumulate_multiplier": self.accumulate_multiplier,
            "minimum_confidence_multiplier": (
                self.minimum_confidence_multiplier
            ),
            "conditional_eligibility_multiplier": (
                self.conditional_eligibility_multiplier
            ),
            "maximum_single_decision_fraction": (
                self.maximum_single_decision_fraction
            ),
        }

        for name, value in ratio_fields.items():
            if not 0.0 <= float(value) <= 1.0:
                raise AllocationConfigurationError(
                    f"{name} must be between 0.0 and 1.0."
                )

        if self.minimum_recommended_allocation < Decimal("0"):
            raise AllocationConfigurationError(
                "minimum_recommended_allocation cannot be negative."
            )

        if self.rounding_increment <= Decimal("0"):
            raise AllocationConfigurationError(
                "rounding_increment must be positive."
            )
