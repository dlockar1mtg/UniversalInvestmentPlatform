"""Normalization result records and shared helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from .score_component import DataAvailability
from .validation import to_decimal, validate_non_empty_text, validate_score


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Immutable diagnostic output from a normalization strategy."""

    raw_value: Any
    normalized_score: Decimal | None
    strategy: str
    availability: DataAvailability = DataAvailability.AVAILABLE
    clipped: bool = False
    warning: str | None = None
    diagnostics: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "strategy",
            validate_non_empty_text(self.strategy, "strategy"),
        )

        if self.availability is DataAvailability.AVAILABLE:
            if self.normalized_score is None:
                raise ValueError("Available normalization results require a score.")
            object.__setattr__(
                self,
                "normalized_score",
                validate_score(self.normalized_score, "normalized_score"),
            )
        elif self.normalized_score is not None:
            raise ValueError("Unavailable normalization results must not contain a score.")

        if self.warning is not None:
            object.__setattr__(
                self,
                "warning",
                validate_non_empty_text(self.warning, "warning"),
            )

        object.__setattr__(
            self,
            "diagnostics",
            MappingProxyType(dict(self.diagnostics or {})),
        )


def clip_decimal(
    value: Decimal | int | float | str,
    minimum: Decimal | int | float | str,
    maximum: Decimal | int | float | str,
) -> tuple[Decimal, bool]:
    """Clip a numeric value to a closed interval and report whether clipping occurred."""
    decimal_value = to_decimal(value, "value")
    decimal_minimum = to_decimal(minimum, "minimum")
    decimal_maximum = to_decimal(maximum, "maximum")
    if decimal_minimum >= decimal_maximum:
        raise ValueError("minimum must be less than maximum.")
    clipped_value = min(max(decimal_value, decimal_minimum), decimal_maximum)
    return clipped_value, clipped_value != decimal_value
