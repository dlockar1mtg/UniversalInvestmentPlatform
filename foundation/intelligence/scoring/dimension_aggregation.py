"""Dimension-level score aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Iterable, Mapping

from .score_component import DataAvailability, ScoreComponent
from .score_dimension import ScoreDimension
from .validation import ZERO, validate_score, validate_unit_interval


@dataclass(frozen=True, slots=True)
class DimensionAggregation:
    """Aggregated score and coverage diagnostics for one dimension."""

    dimension: ScoreDimension
    score: Decimal | None
    coverage_ratio: Decimal
    weighted_confidence: Decimal
    available_weight: Decimal
    total_applicable_weight: Decimal
    component_count: int
    available_component_count: int
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.score is not None:
            object.__setattr__(self, "score", validate_score(self.score, "score"))
        object.__setattr__(
            self,
            "coverage_ratio",
            validate_unit_interval(self.coverage_ratio, "coverage_ratio"),
        )
        object.__setattr__(
            self,
            "weighted_confidence",
            validate_unit_interval(self.weighted_confidence, "weighted_confidence"),
        )


def aggregate_dimension(
    dimension: ScoreDimension,
    components: Iterable[ScoreComponent],
) -> DimensionAggregation:
    """Aggregate available components within a single score dimension."""
    selected = tuple(component for component in components if component.dimension is dimension)
    if not selected:
        return DimensionAggregation(
            dimension=dimension,
            score=None,
            coverage_ratio=Decimal("0"),
            weighted_confidence=Decimal("0"),
            available_weight=Decimal("0"),
            total_applicable_weight=Decimal("0"),
            component_count=0,
            available_component_count=0,
            warnings=("No components supplied for dimension.",),
        )

    applicable = tuple(
        component
        for component in selected
        if component.availability is not DataAvailability.NOT_APPLICABLE
    )
    available = tuple(
        component
        for component in applicable
        if component.availability is DataAvailability.AVAILABLE
    )

    total_applicable_weight = sum((component.weight for component in applicable), ZERO)
    available_weight = sum((component.weight for component in available), ZERO)

    if total_applicable_weight == ZERO:
        return DimensionAggregation(
            dimension=dimension,
            score=None,
            coverage_ratio=Decimal("1"),
            weighted_confidence=Decimal("1"),
            available_weight=Decimal("0"),
            total_applicable_weight=Decimal("0"),
            component_count=len(selected),
            available_component_count=0,
            warnings=("Dimension contains only not-applicable components.",),
        )

    coverage_ratio = available_weight / total_applicable_weight
    warnings = tuple(
        component.warning
        for component in applicable
        if component.warning
    )

    if available_weight == ZERO:
        return DimensionAggregation(
            dimension=dimension,
            score=None,
            coverage_ratio=coverage_ratio,
            weighted_confidence=Decimal("0"),
            available_weight=available_weight,
            total_applicable_weight=total_applicable_weight,
            component_count=len(selected),
            available_component_count=0,
            warnings=warnings or ("No available components for dimension.",),
        )

    weighted_score = sum(
        component.normalized_score * component.weight
        for component in available
        if component.normalized_score is not None
    ) / available_weight
    weighted_confidence = sum(
        component.confidence * component.weight
        for component in available
    ) / available_weight

    return DimensionAggregation(
        dimension=dimension,
        score=weighted_score,
        coverage_ratio=coverage_ratio,
        weighted_confidence=weighted_confidence,
        available_weight=available_weight,
        total_applicable_weight=total_applicable_weight,
        component_count=len(selected),
        available_component_count=len(available),
        warnings=warnings,
    )


def aggregate_dimensions(
    components: Iterable[ScoreComponent],
) -> Mapping[ScoreDimension, DimensionAggregation]:
    """Aggregate all dimensions present in the supplied components."""
    component_tuple = tuple(components)
    dimensions = tuple(dict.fromkeys(component.dimension for component in component_tuple))
    return MappingProxyType(
        {
            dimension: aggregate_dimension(dimension, component_tuple)
            for dimension in dimensions
        }
    )
