"""Generate structured explanations from composite scoring diagnostics."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .composite_engine import CompositeScore
from .explanation import (
    AdjustmentExplanation,
    DimensionContribution,
    MissingDataImpact,
    ScoreExplanation,
)
from .score_dimension import ScoreDimension


QUANTUM = Decimal("0.01")


def _direction(score: Decimal) -> str:
    if score >= Decimal("65"):
        return "positive"
    if score <= Decimal("45"):
        return "negative"
    return "neutral"


def _display_dimension(dimension: ScoreDimension) -> str:
    return dimension.value.replace("_", " ").title()


class ExplanationEngine:
    """Turn score internals into consistent explanations and audit records."""

    def explain(self, composite: CompositeScore) -> ScoreExplanation:
        result = composite.result
        diagnostics = composite.diagnostics

        contribution_rows: list[tuple[ScoreDimension, Decimal, Decimal, Decimal]] = []
        for dimension, weight in diagnostics.used_dimension_weights.items():
            aggregation = diagnostics.dimension_aggregations[dimension]
            if aggregation.score is None:
                continue
            contribution = aggregation.score * weight
            contribution_rows.append(
                (dimension, aggregation.score, weight, contribution)
            )

        ranked = sorted(
            contribution_rows,
            key=lambda row: row[3],
            reverse=True,
        )

        contributions = tuple(
            DimensionContribution(
                dimension=dimension,
                dimension_score=score.quantize(QUANTUM, rounding=ROUND_HALF_UP),
                normalized_weight=weight,
                weighted_contribution=contribution.quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_UP,
                ),
                rank=index,
                direction=_direction(score),
            )
            for index, (dimension, score, weight, contribution) in enumerate(
                ranked,
                start=1,
            )
        )

        positive = tuple(
            _display_dimension(item.dimension)
            for item in contributions
            if item.direction == "positive"
        )[:3]
        negative = tuple(
            _display_dimension(item.dimension)
            for item in sorted(
                contributions,
                key=lambda item: item.dimension_score,
            )
            if item.direction == "negative"
        )[:3]

        confidence = diagnostics.confidence_adjustment
        risk = diagnostics.risk_adjustment
        adjustments = (
            AdjustmentExplanation(
                name="confidence",
                input_score=confidence.raw_score,
                multiplier=confidence.multiplier,
                output_score=confidence.adjusted_score,
                impact_points=(confidence.adjusted_score - confidence.raw_score).quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_UP,
                ),
                explanation=(
                    f"Confidence of {confidence.confidence_score.quantize(QUANTUM)} "
                    f"applied a {confidence.multiplier.quantize(Decimal('0.0001'))} multiplier."
                ),
            ),
            AdjustmentExplanation(
                name="risk",
                input_score=risk.input_score,
                multiplier=risk.multiplier,
                output_score=risk.adjusted_score,
                impact_points=(risk.adjusted_score - risk.input_score).quantize(
                    QUANTUM,
                    rounding=ROUND_HALF_UP,
                ),
                explanation=(
                    f"Risk score of {risk.risk_score.quantize(QUANTUM)} "
                    f"applied a {risk.multiplier.quantize(Decimal('0.0001'))} multiplier."
                ),
            ),
        )

        missing_impacts: list[MissingDataImpact] = []
        omitted = set(diagnostics.omitted_dimensions)
        for dimension, aggregation in diagnostics.dimension_aggregations.items():
            if aggregation.coverage_ratio < Decimal("1") or dimension in omitted:
                missing_impacts.append(
                    MissingDataImpact(
                        dimension=dimension,
                        coverage_ratio=aggregation.coverage_ratio,
                        omitted_from_score=dimension in omitted,
                        message=(
                            f"{_display_dimension(dimension)} coverage was "
                            f"{(aggregation.coverage_ratio * 100).quantize(QUANTUM)}%."
                        ),
                    )
                )

        strongest = positive[0] if positive else "balanced evidence"
        weakest = negative[0] if negative else "no severe dimension weakness"
        headline = (
            f"{result.asset_id} scored {result.final_score} "
            f"and was classified as {result.score_band.replace('_', ' ')}."
        )
        summary = (
            f"The strongest support came from {strongest}. "
            f"The main concern was {weakest}. "
            f"Overall data coverage was "
            f"{(result.coverage_ratio * 100).quantize(QUANTUM)}%."
        )

        audit_record = {
            "asset_id": result.asset_id,
            "asset_class": result.asset_class,
            "as_of_date": result.as_of_date.isoformat(),
            "model_id": result.profile_id,
            "model_version": result.profile_version,
            "raw_composite_score": str(result.raw_composite_score),
            "confidence_score": str(result.confidence_score),
            "confidence_adjusted_score": str(result.confidence_adjusted_score),
            "risk_adjusted_score": str(result.risk_adjusted_score),
            "final_score": str(result.final_score),
            "score_band": result.score_band,
            "coverage_ratio": str(result.coverage_ratio),
            "dimension_scores": {
                dimension.value: str(score)
                for dimension, score in result.dimension_scores.items()
            },
            "used_dimension_weights": {
                dimension.value: str(weight)
                for dimension, weight in diagnostics.used_dimension_weights.items()
            },
            "omitted_dimensions": [
                dimension.value for dimension in diagnostics.omitted_dimensions
            ],
            "warnings": list(result.warnings),
        }

        return ScoreExplanation(
            asset_id=result.asset_id,
            model_id=result.profile_id,
            model_version=result.profile_version,
            final_score=result.final_score,
            score_band=result.score_band,
            headline=headline,
            summary=summary,
            contributions=contributions,
            positive_drivers=positive,
            negative_drivers=negative,
            adjustments=adjustments,
            missing_data_impacts=tuple(missing_impacts),
            warnings=result.warnings,
            audit_record=audit_record,
        )
