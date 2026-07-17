"""Shared validation helpers for historical validation contracts."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable

ZERO = Decimal("0")
ONE = Decimal("1")
ONE_HUNDRED = Decimal("100")


def to_decimal(value: Decimal | int | float | str, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not bool.")
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be decimal-compatible.") from exc


def validate_non_empty_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty.")
    return cleaned


def validate_score(value: Decimal | int | float | str, field_name: str) -> Decimal:
    decimal_value = to_decimal(value, field_name)
    if decimal_value < ZERO or decimal_value > ONE_HUNDRED:
        raise ValueError(f"{field_name} must be between 0 and 100 inclusive.")
    return decimal_value


def validate_unit_interval(
    value: Decimal | int | float | str,
    field_name: str,
) -> Decimal:
    decimal_value = to_decimal(value, field_name)
    if decimal_value < ZERO or decimal_value > ONE:
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive.")
    return decimal_value


def validate_positive_integer(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return value


def validate_horizons(horizons: Iterable[int]) -> tuple[int, ...]:
    normalized = tuple(validate_positive_integer(item, "horizon") for item in horizons)
    if not normalized:
        raise ValueError("At least one horizon is required.")
    if len(normalized) != len(set(normalized)):
        raise ValueError("Horizons must be unique.")
    return tuple(sorted(normalized))
