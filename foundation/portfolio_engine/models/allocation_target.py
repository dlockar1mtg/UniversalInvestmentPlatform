"""Portfolio allocation target model."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from .enums import AssetCategory


@dataclass(slots=True)
class AllocationTarget:
    portfolio_id: UUID
    category: AssetCategory
    target_weight: Decimal
    minimum_weight: Decimal
    maximum_weight: Decimal
    target_id: UUID = field(default_factory=uuid4)
    priority: int = 100
    minimum_purchase_amount: Decimal = Decimal("0")
    allow_fractional: bool = True

    def __post_init__(self) -> None:
        for name in (
            "target_weight",
            "minimum_weight",
            "maximum_weight",
            "minimum_purchase_amount",
        ):
            setattr(self, name, Decimal(str(getattr(self, name))))

        if not Decimal("0") <= self.minimum_weight <= Decimal("1"):
            raise ValueError("Minimum weight must be between 0 and 1.")
        if not Decimal("0") <= self.target_weight <= Decimal("1"):
            raise ValueError("Target weight must be between 0 and 1.")
        if not Decimal("0") <= self.maximum_weight <= Decimal("1"):
            raise ValueError("Maximum weight must be between 0 and 1.")
        if not self.minimum_weight <= self.target_weight <= self.maximum_weight:
            raise ValueError("Target weight must fall inside its allocation band.")
        if self.minimum_purchase_amount < 0:
            raise ValueError("Minimum purchase amount cannot be negative.")
