"""
Serialization utilities for explainable forecast intelligence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from types import MappingProxyType
import json


def _serialize(value):
    """
    Recursively converts immutable forecasting objects into JSON-safe objects.
    """

    if is_dataclass(value):
        return {
            field.name: _serialize(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, (MappingProxyType, Mapping)):
        return {
            str(k): _serialize(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]

    return value


def explanation_to_dict(explanation):
    """
    Convert explanation to JSON-safe dictionary.
    """
    return _serialize(explanation)


def explanation_to_json(
    explanation,
    *,
    indent: int | None = 2,
):
    """
    Deterministic JSON serialization.
    """
    return json.dumps(
        explanation_to_dict(explanation),
        indent=indent,
        sort_keys=True,
    )