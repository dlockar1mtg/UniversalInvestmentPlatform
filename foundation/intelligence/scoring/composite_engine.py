"""Weighted universal composite scoring engine."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from types import MappingProxyType
from typing import Mapping

from .confidence_adjustment import ConfidenceAdjustment, apply_confidence_adjustment
from .dimension_aggregation import DimensionAggregation, aggregate_dimensions
from .risk_adjustment import RiskAdjustment, apply_risk_adjustment
from .score_band import classify_score
from .score_dimension import ScoreDimension
from .score_input import ScoreInput
from .score_result import ScoreResult
from .validation import ZERO


SCORE_QUANTUM = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CompositeDiagnostics:
    """Intermediate calculations preserved for audit and explanation."""

    dimension_aggregations: Mapping[ScoreDimension, DimensionAggregation]
    used_dimension_weights: Mapping[ScoreDimension, Decimal]
    omitted_dimensions: tuple[ScoreDimension, ...]
    raw_composite_score: Decimal
    coverage_ratio: Decimal
    confidence_score: Decimal
    confidence_adjustment: ConfidenceAdjustment
    risk_adjustment: RiskAdjustment
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dimension_aggregations",
            MappingProxyType(dict(self.dimension_aggregations)),
        )
        object.__setattr__(
            self,
            "used_dimension_weights",
            MappingProxyType(dict(self.used_dimension_weights)),
        )


@dataclass(frozen=True, slots=True)
class CompositeScore:
    """Final score result plus complete internal diagnostics."""

    result: ScoreResult
    diagnostics: CompositeDiagnostics


class CompositeScoringEngine:
    """Create a universal score from normalized score components."""

    def score(self, scoring_input: ScoreInput) -> CompositeScore:
        aggregations = aggregate_dimensions(scoring_input.components)
        profile = scoring_input.profile

        usable: dict[ScoreDimension, DimensionAggregation] = {}
        omitted: list[ScoreDimension] = []
        warnings: list[str] = []

        for dimension, configured_weight in profile.dimension_weights.items():
            aggregation = aggregations.get(dimension)
            if aggregation is None or aggregation.score is None:
                omitted.append(dimension)
                warnings.append(f"Dimension omitted: {dimension.value}.")
                continue
            if configured_weight == ZERO:
                omitted.append(dimension)
                continue
            usable[dimension] = aggregation
            warnings.extend(aggregation.warnings)

        total_used_weight = sum(
            (profile.dimension_weights[dimension] for dimension in usable),
            ZERO,
        )
        if total_used_weight == ZERO:
            raise ValueError("No scorable dimensions are available.")

        used_weights = {
            dimension: profile.dimension_weights[dimension] / total_used_weight
            for dimension in usable
        }

        raw_composite = sum(
            usable[dimension].score * used_weights[dimension]
            for dimension in usable
            if usable[dimension].score is not None
        )

        # Coverage is measured against all applicable profile dimensions, not only
        # dimensions that produced a score. Unavailable, stale, invalid, or
        # insufficient-history dimensions therefore reduce coverage. A dimension
        # containing only NOT_APPLICABLE components is removed from the denominator.
        coverage_numerator = ZERO
        coverage_denominator = ZERO
        for dimension, configured_weight in profile.dimension_weights.items():
            if configured_weight == ZERO:
                continue
            aggregation = aggregations.get(dimension)
            if (
                aggregation is not None
                and aggregation.total_applicable_weight == ZERO
                and aggregation.component_count > 0
            ):
                continue
            coverage_denominator += configured_weight
            if aggregation is not None:
                coverage_numerator += aggregation.coverage_ratio * configured_weight

        coverage_ratio = (
            coverage_numerator / coverage_denominator
            if coverage_denominator > ZERO
            else Decimal("1")
        )

        confidence_score = sum(
            usable[dimension].weighted_confidence
            * used_weights[dimension]
            * Decimal("100")
            for dimension in usable
        )

        if coverage_ratio < profile.minimum_coverage:
            warnings.append(
                f"Coverage below minimum: {coverage_ratio} < {profile.minimum_coverage}."
            )

        confidence_adjustment = apply_confidence_adjustment(
            raw_composite,
            confidence_score,
            profile.confidence_floor,
        )

        risk_aggregation = usable.get(ScoreDimension.RISK)
        risk_score = (
            risk_aggregation.score
            if risk_aggregation is not None and risk_aggregation.score is not None
            else Decimal("100")
        )
        if risk_aggregation is None:
            warnings.append("Risk dimension unavailable; no risk penalty applied.")

        risk_adjustment = apply_risk_adjustment(
            confidence_adjustment.adjusted_score,
            risk_score,
            profile.maximum_risk_penalty,
        )

        final_score = risk_adjustment.adjusted_score.quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        raw_score_quantized = raw_composite.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
        confidence_quantized = confidence_score.quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        confidence_adjusted_quantized = confidence_adjustment.adjusted_score.quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        risk_adjusted_quantized = risk_adjustment.adjusted_score.quantize(
            SCORE_QUANTUM,
            rounding=ROUND_HALF_UP,
        )

        band = classify_score(final_score)
        dimension_scores = {
            dimension: aggregation.score.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
            for dimension, aggregation in usable.items()
            if aggregation.score is not None
        }

        positive_drivers = tuple(
            dimension.value
            for dimension, score in sorted(
                dimension_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
        )
        negative_drivers = tuple(
            dimension.value
            for dimension, score in sorted(
                dimension_scores.items(),
                key=lambda item: item[1],
            )[:3]
        )

        result = ScoreResult(
            asset_id=scoring_input.asset_id,
            asset_class=scoring_input.asset_class,
            as_of_date=scoring_input.as_of_date,
            profile_id=profile.profile_id,
            profile_version=profile.version,
            raw_composite_score=raw_score_quantized,
            confidence_score=confidence_quantized,
            confidence_adjusted_score=confidence_adjusted_quantized,
            risk_adjusted_score=risk_adjusted_quantized,
            final_score=final_score,
            score_band=band.name,
            coverage_ratio=coverage_ratio,
            dimension_scores=dimension_scores,
            positive_drivers=positive_drivers,
            negative_drivers=negative_drivers,
            warnings=tuple(dict.fromkeys(warnings)),
        )

        diagnostics = CompositeDiagnostics(
            dimension_aggregations=aggregations,
            used_dimension_weights=used_weights,
            omitted_dimensions=tuple(omitted),
            raw_composite_score=raw_composite,
            coverage_ratio=coverage_ratio,
            confidence_score=confidence_score,
            confidence_adjustment=confidence_adjustment,
            risk_adjustment=risk_adjustment,
            warnings=result.warnings,
        )
        return CompositeScore(result=result, diagnostics=diagnostics)
