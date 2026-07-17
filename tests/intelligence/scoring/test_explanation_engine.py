from datetime import date
from decimal import Decimal

from foundation.intelligence.scoring import (
    CompositeScoringEngine,
    DataAvailability,
    ExplanationEngine,
    ScoreComponent,
    ScoreDimension,
    ScoreInput,
    ScoringProfile,
)


def component(
    name: str,
    dimension: ScoreDimension,
    score: str | None,
    *,
    availability: DataAvailability = DataAvailability.AVAILABLE,
    confidence: str = "1",
) -> ScoreComponent:
    return ScoreComponent(
        metric_name=name,
        dimension=dimension,
        availability=availability,
        raw_value=Decimal("1") if score is not None else None,
        normalized_score=Decimal(score) if score is not None else None,
        weight=Decimal("1"),
        confidence=Decimal(confidence),
        source="fixture",
        calculation_method="fixture",
    )


def build_composite():
    profile = ScoringProfile(
        profile_id="crypto_profile_v1",
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
    scoring_input = ScoreInput(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile,
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "90", confidence="0.9"),
            component("quality", ScoreDimension.QUALITY, "80", confidence="0.8"),
            component("risk", ScoreDimension.RISK, "40", confidence="0.7"),
        ),
    )
    return CompositeScoringEngine().score(scoring_input)


def test_explanation_contains_ranked_contributions() -> None:
    explanation = ExplanationEngine().explain(build_composite())
    assert len(explanation.contributions) == 3
    assert explanation.contributions[0].rank == 1
    assert explanation.contributions[0].weighted_contribution >= explanation.contributions[1].weighted_contribution


def test_explanation_contains_adjustment_impacts() -> None:
    explanation = ExplanationEngine().explain(build_composite())
    assert [item.name for item in explanation.adjustments] == ["confidence", "risk"]
    assert explanation.adjustments[0].impact_points <= Decimal("0")
    assert explanation.adjustments[1].impact_points <= Decimal("0")


def test_explanation_identifies_positive_and_negative_drivers() -> None:
    explanation = ExplanationEngine().explain(build_composite())
    assert "Return Potential" in explanation.positive_drivers
    assert "Risk" in explanation.negative_drivers


def test_audit_record_contains_reproducibility_fields() -> None:
    explanation = ExplanationEngine().explain(build_composite())
    assert explanation.audit_record["model_id"] == "crypto_profile_v1"
    assert explanation.audit_record["model_version"] == "1.0.0"
    assert explanation.audit_record["as_of_date"] == "2026-07-17"


def test_missing_dimension_is_explained() -> None:
    profile = ScoringProfile(
        profile_id="test_profile",
        asset_class="crypto",
        version="1.0.0",
        dimension_weights={
            ScoreDimension.RETURN_POTENTIAL: Decimal("0.5"),
            ScoreDimension.RISK: Decimal("0.5"),
        },
        minimum_coverage=Decimal("0.7"),
        confidence_floor=Decimal("0.7"),
        maximum_risk_penalty=Decimal("0.2"),
    )
    scoring_input = ScoreInput(
        asset_id="crypto:test",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile=profile,
        components=(
            component("return", ScoreDimension.RETURN_POTENTIAL, "80"),
            component(
                "risk",
                ScoreDimension.RISK,
                None,
                availability=DataAvailability.UNAVAILABLE,
            ),
        ),
    )
    explanation = ExplanationEngine().explain(
        CompositeScoringEngine().score(scoring_input)
    )
    assert len(explanation.missing_data_impacts) == 1
    assert explanation.missing_data_impacts[0].dimension is ScoreDimension.RISK
    assert explanation.missing_data_impacts[0].omitted_from_score is True
