from datetime import date
from decimal import Decimal

import pytest

from foundation.intelligence.scoring import (
    CompositeScoringEngine,
    DataAvailability,
    ScoreComponent,
    ScoreDimension,
    ScoreInput,
    ScoringProfile,
)


def component(
    metric_name: str,
    dimension: ScoreDimension,
    score: str | None,
    *,
    weight: str = "1",
    confidence: str = "1",
    availability: DataAvailability = DataAvailability.AVAILABLE,
) -> ScoreComponent:
    return ScoreComponent(
        metric_name=metric_name,
        dimension=dimension,
        availability=availability,
        raw_value=Decimal("1") if score is not None else None,
        normalized_score=Decimal(score) if score is not None else None,
        weight=Decimal(weight),
        confidence=Decimal(confidence),
        source="test",
        calculation_method="fixture",
    )


def profile() -> ScoringProfile:
    return ScoringProfile(
        profile_id="crypto_core_v1",
        asset_class="crypto",
        version="1.0.0",
        dimension_weights={
            ScoreDimension.RETURN_POTENTIAL: Decimal("0.40"),
            ScoreDimension.QUALITY: Decimal("0.30"),
            ScoreDimension.RISK: Decimal("0.30"),
        },
        minimum_coverage=Decimal("0.70"),
        confidence_floor=Decimal("0.70"),
        maximum_risk_penalty=Decimal("0.20"),
    )


def test_dimension_aggregation_uses_component_weights() -> None:
    scoring_input = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component("return_a", ScoreDimension.RETURN_POTENTIAL, "80", weight="0.75"),
            component("return_b", ScoreDimension.RETURN_POTENTIAL, "40", weight="0.25"),
            component("quality", ScoreDimension.QUALITY, "90"),
            component("risk", ScoreDimension.RISK, "70"),
        ),
    )
    result = CompositeScoringEngine().score(scoring_input)
    assert result.result.dimension_scores[ScoreDimension.RETURN_POTENTIAL] == Decimal("70.00")


def test_composite_score_is_deterministic() -> None:
    scoring_input = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "80", confidence="0.9"),
            component("quality", ScoreDimension.QUALITY, "90", confidence="0.8"),
            component("risk", ScoreDimension.RISK, "70", confidence="0.7"),
        ),
    )
    first = CompositeScoringEngine().score(scoring_input)
    second = CompositeScoringEngine().score(scoring_input)
    assert first == second


def test_missing_component_reduces_coverage_not_score_to_zero() -> None:
    scoring_input = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "80"),
            component(
                "quality",
                ScoreDimension.QUALITY,
                None,
                availability=DataAvailability.UNAVAILABLE,
            ),
            component("risk", ScoreDimension.RISK, "70"),
        ),
    )
    output = CompositeScoringEngine().score(scoring_input)
    assert output.result.final_score > Decimal("0")
    assert output.result.coverage_ratio < Decimal("1")
    assert any("quality" in warning for warning in output.result.warnings)


def test_not_applicable_component_does_not_reduce_coverage() -> None:
    scoring_input = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "80"),
            component("quality", ScoreDimension.QUALITY, "90"),
            component("risk", ScoreDimension.RISK, "70"),
            component(
                "risk_extra",
                ScoreDimension.RISK,
                None,
                availability=DataAvailability.NOT_APPLICABLE,
            ),
        ),
    )
    output = CompositeScoringEngine().score(scoring_input)
    assert output.result.coverage_ratio == Decimal("1")


def test_low_confidence_reduces_final_score() -> None:
    high_confidence = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "80", confidence="1"),
            component("quality", ScoreDimension.QUALITY, "90", confidence="1"),
            component("risk", ScoreDimension.RISK, "70", confidence="1"),
        ),
    )
    low_confidence = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "80", confidence="0.2"),
            component("quality", ScoreDimension.QUALITY, "90", confidence="0.2"),
            component("risk", ScoreDimension.RISK, "70", confidence="0.2"),
        ),
    )
    engine = CompositeScoringEngine()
    assert engine.score(low_confidence).result.final_score < engine.score(high_confidence).result.final_score


def test_lower_risk_score_increases_penalty() -> None:
    safer = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "80"),
            component("quality", ScoreDimension.QUALITY, "90"),
            component("risk", ScoreDimension.RISK, "90"),
        ),
    )
    riskier = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "80"),
            component("quality", ScoreDimension.QUALITY, "90"),
            component("risk", ScoreDimension.RISK, "20"),
        ),
    )
    engine = CompositeScoringEngine()
    assert engine.score(riskier).result.final_score < engine.score(safer).result.final_score


def test_engine_rejects_when_no_dimensions_are_scorable() -> None:
    scoring_input = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile(),
        components=(
            component(
                "return",
                ScoreDimension.RETURN_POTENTIAL,
                None,
                availability=DataAvailability.UNAVAILABLE,
            ),
            component(
                "quality",
                ScoreDimension.QUALITY,
                None,
                availability=DataAvailability.UNAVAILABLE,
            ),
            component(
                "risk",
                ScoreDimension.RISK,
                None,
                availability=DataAvailability.UNAVAILABLE,
            ),
        ),
    )
    with pytest.raises(ValueError):
        CompositeScoringEngine().score(scoring_input)
