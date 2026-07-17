"""Descriptive bands for recommendation confidence."""

from enum import StrEnum


class ConfidenceBand(StrEnum):
    """Human-readable confidence categories."""

    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"
