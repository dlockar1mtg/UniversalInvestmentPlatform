"""Score-band contracts and classification logic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .validation import validate_non_empty_text, validate_score


@dataclass(frozen=True, slots=True)
class ScoreBand:
    """Inclusive lower bound and exclusive upper bound score band."""

    name: str
    display_name: str
    minimum_score: Decimal
    maximum_score: Decimal
    interpretation: str
    include_maximum: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", validate_non_empty_text(self.name, "name"))
        object.__setattr__(
            self,
            "display_name",
            validate_non_empty_text(self.display_name, "display_name"),
        )
        object.__setattr__(
            self,
            "interpretation",
            validate_non_empty_text(self.interpretation, "interpretation"),
        )
        minimum = validate_score(self.minimum_score, "minimum_score")
        maximum = validate_score(self.maximum_score, "maximum_score")
        if minimum >= maximum:
            raise ValueError("minimum_score must be less than maximum_score.")
        object.__setattr__(self, "minimum_score", minimum)
        object.__setattr__(self, "maximum_score", maximum)

    def contains(self, score: Decimal | int | float | str) -> bool:
        value = validate_score(score)
        if self.include_maximum:
            return self.minimum_score <= value <= self.maximum_score
        return self.minimum_score <= value < self.maximum_score


DEFAULT_SCORE_BANDS: tuple[ScoreBand, ...] = (
    ScoreBand("critical", "Critical", Decimal("0"), Decimal("20"), "Extremely unfavorable"),
    ScoreBand("very_weak", "Very Weak", Decimal("20"), Decimal("30"), "Major concerns"),
    ScoreBand("weak", "Weak", Decimal("30"), Decimal("40"), "Unfavorable"),
    ScoreBand("moderately_negative", "Moderately Negative", Decimal("40"), Decimal("50"), "Some concerns"),
    ScoreBand("neutral", "Neutral", Decimal("50"), Decimal("60"), "Balanced evidence"),
    ScoreBand("moderately_positive", "Moderately Positive", Decimal("60"), Decimal("70"), "Somewhat favorable"),
    ScoreBand("strong", "Strong", Decimal("70"), Decimal("80"), "Favorable"),
    ScoreBand("very_strong", "Very Strong", Decimal("80"), Decimal("90"), "Strong opportunity"),
    ScoreBand("exceptional", "Exceptional", Decimal("90"), Decimal("100"), "Extremely strong evidence", True),
)


def validate_score_bands(bands: Iterable[ScoreBand]) -> tuple[ScoreBand, ...]:
    """Validate complete, ordered, non-overlapping coverage from 0 to 100."""
    ordered = tuple(sorted(bands, key=lambda band: band.minimum_score))
    if not ordered:
        raise ValueError("At least one score band is required.")
    if ordered[0].minimum_score != Decimal("0"):
        raise ValueError("Score bands must begin at 0.")
    if ordered[-1].maximum_score != Decimal("100"):
        raise ValueError("Score bands must end at 100.")
    if not ordered[-1].include_maximum:
        raise ValueError("The final score band must include 100.")
    for previous, current in zip(ordered, ordered[1:]):
        if previous.maximum_score != current.minimum_score:
            raise ValueError("Score bands must not contain gaps or overlaps.")
    return ordered


def classify_score(
    score: Decimal | int | float | str,
    bands: Iterable[ScoreBand] = DEFAULT_SCORE_BANDS,
) -> ScoreBand:
    """Return the band containing the supplied score."""
    value = validate_score(score)
    for band in validate_score_bands(bands):
        if band.contains(value):
            return band
    raise RuntimeError(f"No score band contains score {value}.")
