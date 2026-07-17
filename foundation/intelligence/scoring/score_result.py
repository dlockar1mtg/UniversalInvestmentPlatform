"""Universal score result contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .score_dimension import ScoreDimension
from .validation import (
    validate_non_empty_text,
    validate_score,
    validate_unit_interval,
)


@dataclass(frozen=True, slots=True)
class ScoreResult:
    """Immutable, explainable output from the scoring engine."""

    asset_id: str
    asset_class: str
    as_of_date: date
    profile_id: str
    profile_version: str
    raw_composite_score: Decimal
    confidence_score: Decimal
    confidence_adjusted_score: Decimal
    risk_adjusted_score: Decimal
    final_score: Decimal
    score_band: str
    coverage_ratio: Decimal
    dimension_scores: Mapping[ScoreDimension, Decimal]
    positive_drivers: tuple[str, ...] = ()
    negative_drivers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "asset_id",
            "asset_class",
            "profile_id",
            "profile_version",
            "score_band",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.as_of_date, date):
            raise TypeError("as_of_date must be a datetime.date.")
        for field_name in (
            "raw_composite_score",
            "confidence_score",
            "confidence_adjusted_score",
            "risk_adjusted_score",
            "final_score",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_score(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "coverage_ratio",
            validate_unit_interval(self.coverage_ratio, "coverage_ratio"),
        )
        normalized_dimensions: dict[ScoreDimension, Decimal] = {}
        for dimension, score in self.dimension_scores.items():
            if not isinstance(dimension, ScoreDimension):
                raise TypeError("dimension_scores keys must be ScoreDimension values.")
            normalized_dimensions[dimension] = validate_score(
                score, f"dimension_scores[{dimension.value}]"
            )
        object.__setattr__(
            self,
            "dimension_scores",
            MappingProxyType(normalized_dimensions),
        )
