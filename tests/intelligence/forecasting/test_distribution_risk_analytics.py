"""Tests for Phase 4.3.5 distribution-risk analytics."""

from __future__ import annotations

from datetime import date, datetime, timezone
from statistics import mean, median, pvariance, pstdev

import pytest

from foundation.intelligence.forecasting.models import ForecastHorizon
from foundation.intelligence.forecasting.probability import (
    DistributionFamily,
    DistributionProvenance,
    DistributionRiskAnalyticsEngine,
    DistributionRiskAnalyticsService,
    DistributionRiskGrade,
    DistributionRiskProfile,
    DistributionStatistics,
    DistributionStatus,
    ForecastConfidenceInterval,
    ForecastDistributionResult,
    ForecastPercentile,
)


def distribution(
    *,
    distribution_id: str = "dist-001",
    asset_id: str = "TEST",
    values: tuple[float, ...] = (
        70.0,
        90.0,
        105.0,
        125.0,
        160.0,
    ),
) -> ForecastDistributionResult:
    calculated_mean = mean(values)
    calculated_median = median(values)
    calculated_variance = pvariance(values)
    calculated_standard_deviation = pstdev(values)

    return ForecastDistributionResult(
        distribution_id=distribution_id,
        status=DistributionStatus.VALIDATED,
        asset_id=asset_id,
        asset_class="equity",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        currency="USD",
        family=DistributionFamily.MONTE_CARLO,
        statistics=DistributionStatistics(
            mean=calculated_mean,
            median=calculated_median,
            variance=calculated_variance,
            standard_deviation=calculated_standard_deviation,
            minimum=min(values),
            maximum=max(values),
            skewness=0.0,
            excess_kurtosis=0.0,
            sample_count=len(values),
        ),
        provenance=DistributionProvenance(
            model_name="risk-test-model",
            model_version="1.0.0",
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
        ),
        percentiles=(
            ForecastPercentile(0.05, values[0]),
            ForecastPercentile(0.25, values[1]),
            ForecastPercentile(0.50, values[2]),
            ForecastPercentile(0.75, values[3]),
            ForecastPercentile(0.95, values[4]),
        ),
        confidence_intervals=(
            ForecastConfidenceInterval(
                lower_probability=0.05,
                upper_probability=0.95,
                lower_value=values[0],
                upper_value=values[4],
                coverage=0.90,
            ),
        ),
        probability_above_reference=0.65,
        probability_below_reference=0.35,
        probability_above_target=0.30,
        target_value=130.0,
    )


def test_profile_rejects_duplicate_var_levels() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        DistributionRiskProfile(
            var_confidence_levels=(0.95, 0.95)
        )


def test_profile_requires_var_levels_above_half() -> None:
    with pytest.raises(ValueError, match="must exceed 0.5"):
        DistributionRiskProfile(
            var_confidence_levels=(0.50,)
        )


def test_analyze_returns_expected_core_metrics() -> None:
    result = DistributionRiskAnalyticsEngine().analyze(
        distribution()
    )

    assert result.asset_id == "TEST"
    assert result.volatility >= 0.0
    assert 0.0 <= result.probability_of_loss <= 1.0
    assert len(result.tail_risk) == 3


def test_expected_return_matches_explicit_samples() -> None:
    result = DistributionRiskAnalyticsEngine().analyze(
        distribution(),
        samples=(80.0, 100.0, 140.0),
        probabilities=(0.25, 0.50, 0.25),
    )

    expected = (
        -0.20 * 0.25
        + 0.0 * 0.50
        + 0.40 * 0.25
    )
    assert result.expected_return == pytest.approx(expected)


def test_explicit_probabilities_are_normalized() -> None:
    result = DistributionRiskAnalyticsEngine().analyze(
        distribution(),
        samples=(80.0, 120.0),
        probabilities=(2.0, 2.0),
    )

    assert result.expected_return == pytest.approx(0.0)


def test_probability_count_must_match_samples() -> None:
    with pytest.raises(ValueError, match="match sample count"):
        DistributionRiskAnalyticsEngine().analyze(
            distribution(),
            samples=(80.0, 120.0),
            probabilities=(1.0,),
        )


def test_negative_probabilities_are_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        DistributionRiskAnalyticsEngine().analyze(
            distribution(),
            samples=(80.0, 120.0),
            probabilities=(-1.0, 2.0),
        )


def test_downside_and_upside_probabilities_are_bounded() -> None:
    result = DistributionRiskAnalyticsEngine().analyze(
        distribution()
    )

    assert 0.0 <= result.downside_probability <= 1.0
    assert 0.0 <= result.upside_probability <= 1.0


def test_interval_width_uses_requested_coverage() -> None:
    result = DistributionRiskAnalyticsEngine().analyze(
        distribution(),
        profile=DistributionRiskProfile(
            uncertainty_interval_coverage=0.90
        ),
    )

    assert result.interval_width == pytest.approx(90.0)
    assert result.normalized_interval_width == pytest.approx(
        0.90
    )


def test_missing_interval_is_rejected() -> None:
    with pytest.raises(ValueError, match="does not contain"):
        DistributionRiskAnalyticsEngine().analyze(
            distribution(),
            profile=DistributionRiskProfile(
                uncertainty_interval_coverage=0.50
            ),
        )


def test_tail_risk_is_ordered_by_confidence() -> None:
    result = DistributionRiskAnalyticsEngine().analyze(
        distribution()
    )

    levels = [
        point.confidence_level for point in result.tail_risk
    ]
    assert levels == [0.90, 0.95, 0.99]


def test_expected_shortfall_is_not_above_var() -> None:
    result = DistributionRiskAnalyticsEngine().analyze(
        distribution()
    )

    assert all(
        point.expected_shortfall
        <= point.value_at_risk + 1e-12
        for point in result.tail_risk
    )


def test_risk_score_is_bounded_and_graded() -> None:
    result = DistributionRiskAnalyticsEngine().analyze(
        distribution()
    )

    assert 0.0 <= result.risk_score <= 1.0
    assert isinstance(result.risk_grade, DistributionRiskGrade)


def test_low_risk_distribution_scores_better() -> None:
    engine = DistributionRiskAnalyticsEngine()

    low = engine.analyze(
        distribution(
            distribution_id="low",
            asset_id="LOW",
            values=(98.0, 100.0, 102.0, 104.0, 106.0),
        )
    )
    high = engine.analyze(
        distribution(
            distribution_id="high",
            asset_id="HIGH",
            values=(30.0, 60.0, 100.0, 160.0, 240.0),
        )
    )

    assert low.risk_score < high.risk_score


def test_comparison_ranks_lowest_risk_first() -> None:
    engine = DistributionRiskAnalyticsEngine()

    low = engine.analyze(
        distribution(
            distribution_id="low",
            asset_id="LOW",
            values=(98.0, 100.0, 102.0, 104.0, 106.0),
        )
    )
    high = engine.analyze(
        distribution(
            distribution_id="high",
            asset_id="HIGH",
            values=(30.0, 60.0, 100.0, 160.0, 240.0),
        )
    )
    comparison = engine.compare((high, low))

    assert comparison.entries[0].asset_id == "LOW"
    assert comparison.entries[0].rank == 1
    assert comparison.entries[1].rank == 2


def test_comparison_requires_metrics() -> None:
    with pytest.raises(ValueError, match="At least one"):
        DistributionRiskAnalyticsEngine().compare(())


def test_service_analyzes_distribution() -> None:
    result = DistributionRiskAnalyticsService().analyze_distribution(
        distribution()
    )

    assert result.distribution_id == "dist-001"


def test_service_compares_distributions() -> None:
    result = DistributionRiskAnalyticsService().compare_distributions(
        (
            distribution(
                distribution_id="a",
                asset_id="A",
                values=(95.0, 100.0, 105.0, 110.0, 115.0),
            ),
            distribution(
                distribution_id="b",
                asset_id="B",
                values=(50.0, 80.0, 100.0, 150.0, 220.0),
            ),
        )
    )

    assert len(result.entries) == 2


def test_analysis_is_deterministic() -> None:
    engine = DistributionRiskAnalyticsEngine()

    first = engine.analyze(distribution())
    second = engine.analyze(distribution())

    assert first == second
