from datetime import date
from decimal import Decimal

import pytest

from foundation.intelligence.scoring import (
    DataAvailability,
    ScoreComponent,
    ScoreDimension,
    ScoreInput,
    ScoreResult,
    ScoringProfile,
)


def build_profile() -> ScoringProfile:
    return ScoringProfile(
        profile_id="test_profile_v1",
        asset_class="crypto",
        version="1.0.0",
        dimension_weights={
            ScoreDimension.RETURN_POTENTIAL: Decimal("0.40"),
            ScoreDimension.RISK: Decimal("0.35"),
            ScoreDimension.DATA_CONFIDENCE: Decimal("0.25"),
        },
        minimum_coverage=Decimal("0.70"),
        confidence_floor=Decimal("0.70"),
        maximum_risk_penalty=Decimal("0.20"),
    )


def build_component() -> ScoreComponent:
    return ScoreComponent(
        metric_name="expected_return_1y",
        dimension=ScoreDimension.RETURN_POTENTIAL,
        availability=DataAvailability.AVAILABLE,
        raw_value=Decimal("0.15"),
        normalized_score=Decimal("78"),
        weight=Decimal("1"),
        confidence=Decimal("0.90"),
        source="test",
        calculation_method="fixture",
    )


def test_profile_is_immutable_and_weights_total_one() -> None:
    profile = build_profile()
    assert sum(profile.dimension_weights.values(), Decimal("0")) == Decimal("1.00")
    with pytest.raises(TypeError):
        profile.dimension_weights[ScoreDimension.MOMENTUM] = Decimal("0.1")


def test_profile_rejects_incorrect_weight_total() -> None:
    with pytest.raises(ValueError):
        ScoringProfile(
            profile_id="bad",
            asset_class="crypto",
            version="1.0.0",
            dimension_weights={ScoreDimension.RISK: Decimal("0.5")},
            minimum_coverage=Decimal("0.7"),
            confidence_floor=Decimal("0.7"),
            maximum_risk_penalty=Decimal("0.2"),
        )


def test_available_component_requires_normalized_score() -> None:
    with pytest.raises(ValueError):
        ScoreComponent(
            metric_name="missing_score",
            dimension=ScoreDimension.RISK,
            availability=DataAvailability.AVAILABLE,
            raw_value=Decimal("1"),
            normalized_score=None,
            weight=Decimal("1"),
            confidence=Decimal("1"),
            source="test",
            calculation_method="fixture",
        )


def test_unavailable_component_must_not_have_normalized_score() -> None:
    with pytest.raises(ValueError):
        ScoreComponent(
            metric_name="bad_missing",
            dimension=ScoreDimension.RISK,
            availability=DataAvailability.UNAVAILABLE,
            raw_value=None,
            normalized_score=Decimal("0"),
            weight=Decimal("1"),
            confidence=Decimal("0"),
            source="test",
            calculation_method="fixture",
        )


def test_score_input_requires_matching_asset_class() -> None:
    with pytest.raises(ValueError):
        ScoreInput(
            asset_id="crypto:bitcoin",
            asset_class="etf",
            as_of_date=date(2026, 7, 17),
            profile=build_profile(),
            components=(build_component(),),
        )


def test_score_result_validates_and_freezes_dimension_scores() -> None:
    result = ScoreResult(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        profile_id="test_profile_v1",
        profile_version="1.0.0",
        raw_composite_score=Decimal("78"),
        confidence_score=Decimal("90"),
        confidence_adjusted_score=Decimal("75"),
        risk_adjusted_score=Decimal("72"),
        final_score=Decimal("72"),
        score_band="strong",
        coverage_ratio=Decimal("0.95"),
        dimension_scores={ScoreDimension.RETURN_POTENTIAL: Decimal("78")},
    )
    assert result.final_score == Decimal("72")
    with pytest.raises(TypeError):
        result.dimension_scores[ScoreDimension.RISK] = Decimal("40")
