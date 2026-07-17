"""Structured explainability contracts for universal scoring."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from .score_dimension import ScoreDimension
from .validation import validate_non_empty_text, validate_score, validate_unit_interval


@dataclass(frozen=True, slots=True)
class DimensionContribution:
    """Contribution of one dimension to the raw composite score."""

    dimension: ScoreDimension
    dimension_score: Decimal
    normalized_weight: Decimal
    weighted_contribution: Decimal
    rank: int
    direction: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dimension_score",
            validate_score(self.dimension_score, "dimension_score"),
        )
        object.__setattr__(
            self,
            "normalized_weight",
            validate_unit_interval(self.normalized_weight, "normalized_weight"),
        )
        if self.rank < 1:
            raise ValueError("rank must be at least 1.")
        if self.direction not in {"positive", "negative", "neutral"}:
            raise ValueError("direction must be positive, negative, or neutral.")


@dataclass(frozen=True, slots=True)
class AdjustmentExplanation:
    """Explain one score adjustment step."""

    name: str
    input_score: Decimal
    multiplier: Decimal
    output_score: Decimal
    impact_points: Decimal
    explanation: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", validate_non_empty_text(self.name, "name"))
        object.__setattr__(
            self,
            "input_score",
            validate_score(self.input_score, "input_score"),
        )
        object.__setattr__(
            self,
            "multiplier",
            validate_unit_interval(self.multiplier, "multiplier"),
        )
        object.__setattr__(
            self,
            "output_score",
            validate_score(self.output_score, "output_score"),
        )
        object.__setattr__(
            self,
            "explanation",
            validate_non_empty_text(self.explanation, "explanation"),
        )


@dataclass(frozen=True, slots=True)
class MissingDataImpact:
    """Describe how missing or unusable data affected score coverage."""

    dimension: ScoreDimension
    coverage_ratio: Decimal
    omitted_from_score: bool
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "coverage_ratio",
            validate_unit_interval(self.coverage_ratio, "coverage_ratio"),
        )
        object.__setattr__(
            self,
            "message",
            validate_non_empty_text(self.message, "message"),
        )


@dataclass(frozen=True, slots=True)
class ScoreExplanation:
    """Complete human- and machine-readable score explanation."""

    asset_id: str
    model_id: str
    model_version: str
    final_score: Decimal
    score_band: str
    headline: str
    summary: str
    contributions: tuple[DimensionContribution, ...]
    positive_drivers: tuple[str, ...]
    negative_drivers: tuple[str, ...]
    adjustments: tuple[AdjustmentExplanation, ...]
    missing_data_impacts: tuple[MissingDataImpact, ...]
    warnings: tuple[str, ...]
    audit_record: Mapping[str, Any]

    def __post_init__(self) -> None:
        for field_name in (
            "asset_id",
            "model_id",
            "model_version",
            "score_band",
            "headline",
            "summary",
        ):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "final_score",
            validate_score(self.final_score, "final_score"),
        )
        object.__setattr__(
            self,
            "audit_record",
            MappingProxyType(dict(self.audit_record)),
        )
