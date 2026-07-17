"""Tests for Phase 4.4.3 continuous learning."""

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
    ContinuousLearningEngine,
    ContinuousLearningProfile,
    ContinuousLearningService,
    ForecastArchive,
    ForecastOutcome,
    ForecastOutcomeTracker,
    ForecastPerformanceAnalyticsEngine,
    LearningState,
    ModelLearningSnapshot,
    ModelLearningStatus,
    PerformanceAnalyticsProfile,
    PerformanceGrouping,
    learning_state_from_dict,
    learning_state_to_dict,
    learning_state_to_json,
    load_learning_state,
    save_learning_state,
)


def forecast(
    *,
    forecast_id: str,
    model_name: str,
    point_forecast: float,
) -> UniversalForecast:
    return UniversalForecast(
        forecast_id=forecast_id,
        asset_id="TEST",
        as_of_date=date(2026, 1, 1),
        target_date=date(2027, 1, 1),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        point_forecast=point_forecast,
        currency="USD",
        provenance=ForecastProvenance(
            model_name=model_name,
            model_version="1.0.0",
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 1, 1, 12, 0, tzinfo=timezone.utc
            ),
        ),
        direction=(
            ForecastDirection.UP
            if point_forecast >= 100.0
            else ForecastDirection.DOWN
        ),
        expected_return=point_forecast / 100.0 - 1.0,
        confidence_score=0.80,
        interval=ForecastInterval(
            lower=70.0,
            upper=150.0,
            coverage=0.95,
        ),
    )


def record(
    *,
    forecast_id: str,
    model_name: str,
    point_forecast: float,
    observed_value: float,
):
    item = forecast(
        forecast_id=forecast_id,
        model_name=model_name,
        point_forecast=point_forecast,
    )
    outcome = ForecastOutcome(
        forecast_id=forecast_id,
        asset_id="TEST",
        observation_date=date(2027, 1, 1),
        observed_value=observed_value,
        source="test",
    )
    return ForecastOutcomeTracker().validate(item, outcome)


def scorecards():
    records = (
        record(
            forecast_id="good-1",
            model_name="good",
            point_forecast=110.0,
            observed_value=109.0,
        ),
        record(
            forecast_id="good-2",
            model_name="good",
            point_forecast=110.0,
            observed_value=111.0,
        ),
        record(
            forecast_id="good-3",
            model_name="good",
            point_forecast=110.0,
            observed_value=110.0,
        ),
        record(
            forecast_id="bad-1",
            model_name="bad",
            point_forecast=140.0,
            observed_value=90.0,
        ),
        record(
            forecast_id="bad-2",
            model_name="bad",
            point_forecast=140.0,
            observed_value=95.0,
        ),
        record(
            forecast_id="bad-3",
            model_name="bad",
            point_forecast=140.0,
            observed_value=100.0,
        ),
    )
    return ForecastPerformanceAnalyticsEngine().analyze(
        records,
        grouping=PerformanceGrouping.MODEL,
        profile=PerformanceAnalyticsProfile(
            minimum_sample_size=3
        ),
    ).scorecards


def test_learning_profile_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        ContinuousLearningProfile(
            performance_weight=0.50,
            recency_weight=0.20,
            stability_weight=0.20,
        )


def test_learning_profile_thresholds_are_ordered() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        ContinuousLearningProfile(
            demotion_threshold=0.60,
            watch_threshold=0.50,
        )


def test_empty_scorecards_are_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        ContinuousLearningEngine().learn(())


def test_learning_requires_model_grouping() -> None:
    overall = ForecastPerformanceAnalyticsEngine().analyze(
        (
            record(
                forecast_id="a",
                model_name="good",
                point_forecast=110.0,
                observed_value=109.0,
            ),
        ),
        grouping=PerformanceGrouping.OVERALL,
    ).scorecards

    with pytest.raises(ValueError, match="model-grouped"):
        ContinuousLearningEngine().learn(overall)


def test_equal_weights_are_created_by_default() -> None:
    result = ContinuousLearningEngine().learn(scorecards())

    assert sum(
        signal.current_weight for signal in result.signals
    ) == pytest.approx(1.0)


def test_good_model_earns_higher_reputation() -> None:
    result = ContinuousLearningEngine().learn(scorecards())
    by_key = {item.model_key: item for item in result.signals}

    assert (
        by_key["good:1.0.0"].new_reputation
        > by_key["bad:1.0.0"].new_reputation
    )


def test_good_model_receives_higher_weight() -> None:
    result = ContinuousLearningEngine().learn(scorecards())
    by_key = {item.model_key: item for item in result.signals}

    assert (
        by_key["good:1.0.0"].recommended_weight
        > by_key["bad:1.0.0"].recommended_weight
    )
    assert sum(
        item.recommended_weight for item in result.signals
    ) == pytest.approx(1.0)


def test_weight_change_is_bounded() -> None:
    profile = ContinuousLearningProfile(
        maximum_weight_change=0.05
    )
    result = ContinuousLearningEngine().learn(
        scorecards(),
        current_weights={
            "good:1.0.0": 0.50,
            "bad:1.0.0": 0.50,
        },
        profile=profile,
    )

    assert all(
        abs(item.weight_change) <= 0.051
        for item in result.signals
    )


def test_current_weight_keys_must_match_models() -> None:
    with pytest.raises(ValueError, match="must match"):
        ContinuousLearningEngine().learn(
            scorecards(),
            current_weights={"good:1.0.0": 1.0},
        )


def test_current_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        ContinuousLearningEngine().learn(
            scorecards(),
            current_weights={
                "good:1.0.0": 0.80,
                "bad:1.0.0": 0.80,
            },
        )


def test_prior_state_changes_reputation_baseline() -> None:
    prior = LearningState(
        snapshots=(
            ModelLearningSnapshot(
                model_key="good:1.0.0",
                reputation=0.90,
                adaptive_weight=0.60,
                status=ModelLearningStatus.PROMOTED,
                sample_size=10,
            ),
            ModelLearningSnapshot(
                model_key="bad:1.0.0",
                reputation=0.20,
                adaptive_weight=0.40,
                status=ModelLearningStatus.DEMOTED,
                sample_size=10,
            ),
        )
    )
    result = ContinuousLearningEngine().learn(
        scorecards(),
        prior_state=prior,
    )
    by_key = {item.model_key: item for item in result.signals}

    assert by_key["good:1.0.0"].prior_reputation == 0.90
    assert by_key["bad:1.0.0"].prior_reputation == 0.20


def test_update_count_increments_from_prior_state() -> None:
    prior = LearningState(
        snapshots=(
            ModelLearningSnapshot(
                model_key="good:1.0.0",
                reputation=0.75,
                adaptive_weight=0.60,
                status=ModelLearningStatus.STABLE,
                sample_size=3,
                update_count=4,
            ),
            ModelLearningSnapshot(
                model_key="bad:1.0.0",
                reputation=0.35,
                adaptive_weight=0.40,
                status=ModelLearningStatus.DEMOTED,
                sample_size=3,
                update_count=2,
            ),
        )
    )
    result = ContinuousLearningEngine().learn(
        scorecards(),
        prior_state=prior,
    )
    by_key = {
        item.model_key: item for item in result.state.snapshots
    }

    assert by_key["good:1.0.0"].update_count == 5
    assert by_key["bad:1.0.0"].update_count == 3


def test_ineligible_model_gets_ineligible_status() -> None:
    single = ForecastPerformanceAnalyticsEngine().analyze(
        (
            record(
                forecast_id="one",
                model_name="single",
                point_forecast=110.0,
                observed_value=109.0,
            ),
        ),
        grouping=PerformanceGrouping.MODEL,
        profile=PerformanceAnalyticsProfile(
            minimum_sample_size=3
        ),
    ).scorecards

    result = ContinuousLearningEngine().learn(single)

    assert result.signals[0].status is (
        ModelLearningStatus.INELIGIBLE
    )


def test_learning_state_is_json_safe() -> None:
    state = ContinuousLearningEngine().learn(
        scorecards()
    ).state
    payload = learning_state_to_dict(state)

    assert payload["schema_version"] == "1.0.0"
    assert len(payload["snapshots"]) == 2


def test_learning_state_json_is_deterministic() -> None:
    state = ContinuousLearningEngine().learn(
        scorecards()
    ).state

    assert learning_state_to_json(state) == learning_state_to_json(
        state
    )


def test_learning_state_round_trip() -> None:
    state = ContinuousLearningEngine().learn(
        scorecards()
    ).state
    restored = learning_state_from_dict(
        learning_state_to_dict(state)
    )

    assert restored == state


def test_learning_state_save_and_load(tmp_path) -> None:
    state = ContinuousLearningEngine().learn(
        scorecards()
    ).state
    path = tmp_path / "learning_state.json"

    save_learning_state(state, path)
    restored = load_learning_state(path)

    assert restored == state


def test_service_learns_from_archive() -> None:
    archive = ForecastArchive()
    archive.extend(
        (
            record(
                forecast_id="good-1",
                model_name="good",
                point_forecast=110.0,
                observed_value=109.0,
            ),
            record(
                forecast_id="good-2",
                model_name="good",
                point_forecast=110.0,
                observed_value=111.0,
            ),
            record(
                forecast_id="good-3",
                model_name="good",
                point_forecast=110.0,
                observed_value=110.0,
            ),
        )
    )
    service = ContinuousLearningService(archive=archive)

    result = service.learn_from_archive(
        performance_profile=PerformanceAnalyticsProfile(
            minimum_sample_size=3
        )
    )

    assert len(result.signals) == 1


def test_service_learns_and_saves(tmp_path) -> None:
    archive = ForecastArchive()
    archive.extend(
        (
            record(
                forecast_id="good-1",
                model_name="good",
                point_forecast=110.0,
                observed_value=109.0,
            ),
            record(
                forecast_id="good-2",
                model_name="good",
                point_forecast=110.0,
                observed_value=111.0,
            ),
            record(
                forecast_id="good-3",
                model_name="good",
                point_forecast=110.0,
                observed_value=110.0,
            ),
        )
    )
    service = ContinuousLearningService(archive=archive)
    path = tmp_path / "state.json"

    result = service.learn_and_save(
        path,
        performance_profile=PerformanceAnalyticsProfile(
            minimum_sample_size=3
        ),
    )

    assert path.exists()
    assert service.load_state(path) == result.state


def test_learning_is_deterministic_except_timestamps() -> None:
    engine = ContinuousLearningEngine()

    first = engine.learn(
        scorecards(),
        as_of_date=date(2027, 1, 1),
    )
    second = engine.learn(
        scorecards(),
        as_of_date=date(2027, 1, 1),
    )

    first_signals = {
        item.model_key: (
            item.new_reputation,
            item.recommended_weight,
            item.status,
        )
        for item in first.signals
    }
    second_signals = {
        item.model_key: (
            item.new_reputation,
            item.recommended_weight,
            item.status,
        )
        for item in second.signals
    }

    assert first_signals == second_signals
