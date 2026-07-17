"""Tests for Phase 4.4.2 forecast performance analytics."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastInterval,
    ForecastMethod,
    ForecastProvenance,
    UniversalForecast,
)
from foundation.intelligence.forecasting.validation import (
    ForecastArchive,
    ForecastOutcome,
    ForecastOutcomeTracker,
    ForecastPerformanceAnalyticsEngine,
    ForecastPerformanceAnalyticsService,
    PerformanceAnalyticsProfile,
    PerformanceGrade,
    PerformanceGrouping,
)


def forecast(
    *,
    forecast_id: str,
    asset_id: str = "TEST",
    point_forecast: float = 110.0,
    model_name: str = "model-a",
    model_version: str = "1.0.0",
    horizon: ForecastHorizon = ForecastHorizon.ONE_YEAR,
    direction: ForecastDirection = ForecastDirection.UP,
) -> UniversalForecast:
    return UniversalForecast(
        forecast_id=forecast_id,
        asset_id=asset_id,
        as_of_date=date(2026, 1, 1),
        target_date=date(2027, 1, 1),
        horizon=horizon,
        reference_value=100.0,
        point_forecast=point_forecast,
        currency="USD",
        provenance=ForecastProvenance(
            model_name=model_name,
            model_version=model_version,
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 1, 1, 12, 0, tzinfo=timezone.utc
            ),
        ),
        direction=direction,
        expected_return=point_forecast / 100.0 - 1.0,
        confidence_score=0.80,
        interval=ForecastInterval(
            lower=80.0,
            upper=140.0,
            coverage=0.95,
        ),
    )


def record(
    *,
    forecast_id: str,
    observed_value: float,
    observation_date: date = date(2027, 1, 1),
    asset_id: str = "TEST",
    model_name: str = "model-a",
    model_version: str = "1.0.0",
    point_forecast: float = 110.0,
    horizon: ForecastHorizon = ForecastHorizon.ONE_YEAR,
    direction: ForecastDirection = ForecastDirection.UP,
):
    item = forecast(
        forecast_id=forecast_id,
        asset_id=asset_id,
        point_forecast=point_forecast,
        model_name=model_name,
        model_version=model_version,
        horizon=horizon,
        direction=direction,
    )
    outcome = ForecastOutcome(
        forecast_id=forecast_id,
        asset_id=asset_id,
        observation_date=observation_date,
        observed_value=observed_value,
        source="test",
    )
    return ForecastOutcomeTracker().validate(item, outcome)


def records():
    return (
        record(
            forecast_id="a",
            observed_value=108.0,
            model_name="model-a",
        ),
        record(
            forecast_id="b",
            observed_value=112.0,
            model_name="model-a",
        ),
        record(
            forecast_id="c",
            observed_value=90.0,
            point_forecast=92.0,
            direction=ForecastDirection.DOWN,
            model_name="model-b",
            asset_id="OTHER",
        ),
    )


def test_profile_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        PerformanceAnalyticsProfile(
            direction_weight=0.20,
            error_weight=0.20,
            coverage_weight=0.20,
            bias_weight=0.20,
        )


def test_profile_requires_positive_sample_size() -> None:
    with pytest.raises(ValueError, match="positive"):
        PerformanceAnalyticsProfile(minimum_sample_size=0)


def test_empty_records_are_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        ForecastPerformanceAnalyticsEngine().analyze(())


def test_overall_metrics_are_calculated() -> None:
    report = ForecastPerformanceAnalyticsEngine().analyze(records())
    metrics = report.scorecards[0]

    assert metrics.sample_size == 3
    assert metrics.mae == pytest.approx(2.0)
    assert metrics.rmse == pytest.approx(2.0)


def test_mape_is_calculated() -> None:
    metrics = ForecastPerformanceAnalyticsEngine().analyze(
        records()
    ).scorecards[0]

    expected = (2 / 108 + 2 / 112 + 2 / 90) / 3
    assert metrics.mape == pytest.approx(expected)


def test_smape_is_calculated() -> None:
    metrics = ForecastPerformanceAnalyticsEngine().analyze(
        records()
    ).scorecards[0]

    assert metrics.smape is not None
    assert metrics.smape > 0.0


def test_mean_bias_is_calculated() -> None:
    metrics = ForecastPerformanceAnalyticsEngine().analyze(
        records()
    ).scorecards[0]

    assert metrics.mean_bias == pytest.approx(
        (2.0 - 2.0 + 2.0) / 3
    )


def test_directional_accuracy_is_calculated() -> None:
    metrics = ForecastPerformanceAnalyticsEngine().analyze(
        records()
    ).scorecards[0]

    assert metrics.directional_accuracy == pytest.approx(1.0)


def test_interval_coverage_is_calculated() -> None:
    metrics = ForecastPerformanceAnalyticsEngine().analyze(
        records()
    ).scorecards[0]

    assert metrics.interval_coverage == pytest.approx(1.0)
    assert metrics.interval_coverage_gap == pytest.approx(0.05)


def test_grouping_by_model_creates_scorecards() -> None:
    report = ForecastPerformanceAnalyticsEngine().analyze(
        records(),
        grouping=PerformanceGrouping.MODEL,
    )

    assert len(report.scorecards) == 2
    keys = {item.group_key for item in report.scorecards}
    assert keys == {"model-a:1.0.0", "model-b:1.0.0"}


def test_grouping_by_asset_creates_scorecards() -> None:
    report = ForecastPerformanceAnalyticsEngine().analyze(
        records(),
        grouping=PerformanceGrouping.ASSET,
    )

    assert {item.group_key for item in report.scorecards} == {
        "TEST",
        "OTHER",
    }


def test_grouping_by_horizon_creates_scorecards() -> None:
    report = ForecastPerformanceAnalyticsEngine().analyze(
        records(),
        grouping=PerformanceGrouping.HORIZON,
    )

    assert len(report.scorecards) == 1
    assert report.scorecards[0].group_key == "1y"


def test_rolling_window_filters_old_records() -> None:
    old = record(
        forecast_id="old",
        observed_value=100.0,
        observation_date=date(2027, 1, 1),
    )
    recent = record(
        forecast_id="recent",
        observed_value=108.0,
        observation_date=date(2027, 12, 31),
    )
    report = ForecastPerformanceAnalyticsEngine().analyze(
        (old, recent),
        profile=PerformanceAnalyticsProfile(
            rolling_window_days=30
        ),
        evaluation_date=date(2027, 12, 31),
    )

    assert report.scorecards[0].sample_size == 1


def test_window_that_removes_everything_is_rejected() -> None:
    with pytest.raises(ValueError, match="No records remain"):
        ForecastPerformanceAnalyticsEngine().analyze(
            records(),
            profile=PerformanceAnalyticsProfile(
                rolling_window_days=30
            ),
            evaluation_date=date(2030, 1, 1),
        )


def test_minimum_sample_size_controls_eligibility() -> None:
    report = ForecastPerformanceAnalyticsEngine().analyze(
        records(),
        grouping=PerformanceGrouping.MODEL,
        profile=PerformanceAnalyticsProfile(
            minimum_sample_size=2
        ),
    )
    by_key = {
        item.group_key: item for item in report.scorecards
    }

    assert by_key["model-a:1.0.0"].eligible is True
    assert by_key["model-b:1.0.0"].eligible is False


def test_score_is_bounded_and_graded() -> None:
    metrics = ForecastPerformanceAnalyticsEngine().analyze(
        records()
    ).scorecards[0]

    assert 0.0 <= metrics.score <= 1.0
    assert isinstance(metrics.grade, PerformanceGrade)


def test_better_model_ranks_first() -> None:
    high_quality = (
        record(
            forecast_id="good-1",
            observed_value=109.0,
            model_name="good",
        ),
        record(
            forecast_id="good-2",
            observed_value=111.0,
            model_name="good",
        ),
    )
    low_quality = (
        record(
            forecast_id="bad-1",
            observed_value=50.0,
            model_name="bad",
        ),
        record(
            forecast_id="bad-2",
            observed_value=160.0,
            model_name="bad",
        ),
    )
    report = ForecastPerformanceAnalyticsEngine().analyze(
        high_quality + low_quality,
        grouping=PerformanceGrouping.MODEL,
    )

    assert report.rankings[0].group_key == "good:1.0.0"


def test_ineligible_models_rank_after_eligible_models() -> None:
    report = ForecastPerformanceAnalyticsEngine().analyze(
        records(),
        grouping=PerformanceGrouping.MODEL,
        profile=PerformanceAnalyticsProfile(
            minimum_sample_size=2
        ),
    )

    assert report.rankings[0].eligible is True
    assert report.rankings[-1].eligible is False


def test_service_builds_report_from_archive() -> None:
    archive = ForecastArchive()
    archive.extend(records())
    service = ForecastPerformanceAnalyticsService(
        archive=archive
    )

    report = service.report()

    assert report.generated_for is PerformanceGrouping.OVERALL
    assert report.scorecards[0].sample_size == 3


def test_service_builds_model_leaderboard() -> None:
    archive = ForecastArchive()
    archive.extend(records())
    service = ForecastPerformanceAnalyticsService(
        archive=archive
    )

    report = service.model_leaderboard()

    assert report.generated_for is PerformanceGrouping.MODEL
    assert len(report.rankings) == 2


def test_analysis_is_deterministic() -> None:
    engine = ForecastPerformanceAnalyticsEngine()

    first = engine.analyze(
        records(),
        grouping=PerformanceGrouping.MODEL,
    )
    second = engine.analyze(
        records(),
        grouping=PerformanceGrouping.MODEL,
    )

    assert first == second
