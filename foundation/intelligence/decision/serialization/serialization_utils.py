"""Shared utilities for stable decision serialization."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence

from .serialization_errors import SerializationSchemaError


def to_primitive(value: Any) -> Any:
    """Convert supported decision objects into JSON-safe primitives."""

    if value is None:
        return None

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise SerializationSchemaError(
                "Serialized datetimes must include timezone information."
            )
        return value.isoformat()

    if is_dataclass(value):
        return {
            field.name: to_primitive(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, Mapping):
        return {
            str(key): to_primitive(item)
            for key, item in value.items()
        }

    if isinstance(value, tuple):
        return [to_primitive(item) for item in value]

    if isinstance(value, list):
        return [to_primitive(item) for item in value]

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [to_primitive(item) for item in value]

    if isinstance(value, (str, int, float, bool)):
        return value

    raise SerializationSchemaError(
        f"Unsupported serialized value type: {type(value).__name__}."
    )


def require_mapping(
    value: Any,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    """Validate that a serialized field is mapping-like."""

    if not isinstance(value, Mapping):
        raise SerializationSchemaError(
            f"{field_name} must be a mapping."
        )

    return value


def require_sequence(
    value: Any,
    *,
    field_name: str,
) -> list[Any]:
    """Validate that a serialized field is list-like."""

    if not isinstance(value, list):
        raise SerializationSchemaError(
            f"{field_name} must be a list."
        )

    return value


def require_string(
    value: Any,
    *,
    field_name: str,
) -> str:
    """Validate a required nonblank serialized string."""

    if not isinstance(value, str) or not value.strip():
        raise SerializationSchemaError(
            f"{field_name} must be a nonblank string."
        )

    return value


def parse_datetime(
    value: Any,
    *,
    field_name: str,
) -> datetime:
    """Parse an ISO timestamp and require timezone information."""

    raw = require_string(value, field_name=field_name)

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise SerializationSchemaError(
            f"{field_name} must be a valid ISO datetime."
        ) from exc

    if parsed.tzinfo is None:
        raise SerializationSchemaError(
            f"{field_name} must include timezone information."
        )

    return parsed


def parse_decimal(
    value: Any,
    *,
    field_name: str,
) -> Decimal:
    """Parse a decimal serialized as a string or number."""

    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise SerializationSchemaError(
            f"{field_name} must be decimal-compatible."
        ) from exc

    return parsed
