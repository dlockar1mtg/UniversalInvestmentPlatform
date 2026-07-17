"""Portfolio and capital context supplied to a decision evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from .decision_errors import DecisionValidationError


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Portfolio state relevant to evaluating one investment opportunity."""

    portfolio_id: str
    as_of: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    portfolio_value: Decimal = Decimal("0")
    available_capital: Decimal = Decimal("0")
    current_position_value: Decimal = Decimal("0")
    current_asset_weight: float = 0.0
    current_asset_class_weight: float = 0.0
    target_asset_weight: float | None = None
    target_asset_class_weight: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise DecisionValidationError(
                "portfolio_id cannot be empty."
            )

        if self.as_of.tzinfo is None:
            raise DecisionValidationError(
                "as_of must include timezone information."
            )

        if self.portfolio_value < Decimal("0"):
            raise DecisionValidationError(
                "portfolio_value cannot be negative."
            )

        if self.current_position_value < Decimal("0"):
            raise DecisionValidationError(
                "current_position_value cannot be negative."
            )

        self._validate_weight(
            "current_asset_weight",
            self.current_asset_weight,
        )
        self._validate_weight(
            "current_asset_class_weight",
            self.current_asset_class_weight,
        )

        if self.target_asset_weight is not None:
            self._validate_weight(
                "target_asset_weight",
                self.target_asset_weight,
            )

        if self.target_asset_class_weight is not None:
            self._validate_weight(
                "target_asset_class_weight",
                self.target_asset_class_weight,
            )

    @staticmethod
    def _validate_weight(name: str, value: float) -> None:
        if not 0.0 <= float(value) <= 1.0:
            raise DecisionValidationError(
                f"{name} must be between 0.0 and 1.0."
            )
