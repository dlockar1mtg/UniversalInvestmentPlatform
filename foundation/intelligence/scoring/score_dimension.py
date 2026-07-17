"""Universal scoring dimension definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .validation import validate_non_empty_text


class ScoreDimension(str, Enum):
    """Standardized dimensions available to all scoring profiles."""

    RETURN_POTENTIAL = "return_potential"
    MOMENTUM = "momentum"
    VALUATION = "valuation"
    QUALITY = "quality"
    RISK = "risk"
    LIQUIDITY = "liquidity"
    DIVERSIFICATION = "diversification"
    MACRO_ALIGNMENT = "macro_alignment"
    DATA_CONFIDENCE = "data_confidence"


UNIVERSAL_DIMENSIONS: tuple[ScoreDimension, ...] = tuple(ScoreDimension)


@dataclass(frozen=True, slots=True)
class ScoreDimensionDefinition:
    """Human-readable metadata for a universal score dimension."""

    dimension: ScoreDimension
    display_name: str
    description: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "display_name",
            validate_non_empty_text(self.display_name, "display_name"),
        )
        object.__setattr__(
            self,
            "description",
            validate_non_empty_text(self.description, "description"),
        )
