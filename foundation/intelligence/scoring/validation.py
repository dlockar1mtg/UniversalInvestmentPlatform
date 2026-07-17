"""Shared validation helpers for universal scoring contracts."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Mapping

ZERO = Decimal("0")
ONE = Decimal("1")
ONE_HUNDRED = Decimal("100")
WEIGHT_TOLERANCE = Decimal("0.000001")


def to_decimal(value: Decimal | int | float | str, field_name: str) -> Decimal:
    """Convert a supported numeric value to Decimal safely."""
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not bool.")
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TypeError(f"{field_name} must be a valid decimal-compatible value.") from exc


def validate_score(value: Decimal | int | float | str, field_name: str = "score") -> Decimal:
    """Validate and return a score constrained to 0 through 100."""
    decimal_value = to_decimal(value, field_name)
    if decimal_value < ZERO or decimal_value > ONE_HUNDRED:
        raise ValueError(f"{field_name} must be between 0 and 100 inclusive.")
    return decimal_value


def validate_unit_interval(
    value: Decimal | int | float | str,
    field_name: str,
) -> Decimal:
    """Validate and return a value constrained to 0 through 1."""
    decimal_value = to_decimal(value, field_name)
    if decimal_value < ZERO or decimal_value > ONE:
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive.")
    return decimal_value


def validate_non_negative(
    value: Decimal | int | float | str,
    field_name: str,
) -> Decimal:
    """Validate and return a non-negative Decimal."""
    decimal_value = to_decimal(value, field_name)
    if decimal_value < ZERO:
        raise ValueError(f"{field_name} must be non-negative.")
    return decimal_value


def validate_non_empty_text(value: str, field_name: str) -> str:
    """Validate and return trimmed non-empty text."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty.")
    return cleaned


def validate_weight_total(
    weights: Mapping[str, Decimal],
    expected: Decimal = ONE,
    tolerance: Decimal = WEIGHT_TOLERANCE,
) -> None:
    """Require a mapping of weights to total the expected value."""
    total = sum(weights.values(), ZERO)
    if abs(total - expected) > tolerance:
        raise ValueError(
            f"Weight total must equal {expected}; received {total}."
        )
