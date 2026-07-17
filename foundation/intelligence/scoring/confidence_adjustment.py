"""Confidence adjustment policies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .validation import validate_score, validate_unit_interval


@dataclass(frozen=True, slots=True)
class ConfidenceAdjustment:
    raw_score: Decimal
    confidence_score: Decimal
    confidence_floor: Decimal
    multiplier: Decimal
    adjusted_score: Decimal

    def __post_init__(self) -> None:
        for field_name in ("raw_score", "confidence_score", "adjusted_score"):
            object.__setattr__(
                self,
                field_name,
                validate_score(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "confidence_floor",
            validate_unit_interval(self.confidence_floor, "confidence_floor"),
        )
        object.__setattr__(
            self,
            "multiplier",
            validate_unit_interval(self.multiplier, "multiplier"),
        )


def apply_confidence_adjustment(
    raw_score: Decimal,
    confidence_score: Decimal,
    confidence_floor: Decimal,
) -> ConfidenceAdjustment:
    """Apply a bounded confidence multiplier to a raw score."""
    raw = validate_score(raw_score, "raw_score")
    confidence = validate_score(confidence_score, "confidence_score")
    floor = validate_unit_interval(confidence_floor, "confidence_floor")
    multiplier = floor + (Decimal("1") - floor) * (confidence / Decimal("100"))
    adjusted = raw * multiplier
    return ConfidenceAdjustment(
        raw_score=raw,
        confidence_score=confidence,
        confidence_floor=floor,
        multiplier=multiplier,
        adjusted_score=adjusted,
    )
