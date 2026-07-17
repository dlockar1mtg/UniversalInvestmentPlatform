"""Tests for Phase 4.4.4 forecast drift detection."""

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
    DriftDetectionProfile,
    DriftHistory,
    DriftRecommendation,
    DriftSeverity,
    ForecastArchive,
    ForecastDriftDetectionEngine,
    ForecastDriftDetectionService,
    ForecastOutcome,
    ForecastOutcomeTracker,
    ForecastPerformanceAnalyticsEngine,
    PerformanceAnalyticsProfile,
    PerformanceGrouping,
    drift_history_from_dict,
    drift_history_to_dict,
    drift_history_to_json,
    load_drift_history,
    save_drift_history,
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


def scorecards(
    *,
    model_name: str,
    predictions: tuple[float, ...],
    observations: tuple[float, ...],
):
    records = tuple(
        record(
            forecast_id=f"{model_name}-{index}",
            model_name=model_name,
            point_forecast=prediction,
            observed_value=observation,
        )
        for index, (prediction, observation) in enumerate(
            zip(predictions, observations),
            start=1,
        )
    )
    return ForecastPerformanceAnalyticsEngine().analyze(
        records,
        grouping=PerformanceGrouping.MODEL,
        profile=PerformanceAnalyticsProfile(
            minimum_sample_size=3
        ),
    ).scorecards


def stable_baseline():
    return scorecards(
        model_name="model",
        predictions=(110.0, 111.0, 109.0),
        observations=(109.0, 111.0, 110.0),
    )


def stable_current():
    return scorecards(
        model_name="model",
        predictions=(110.0, 111.0, 109.0),
        observations=(109.5, 110.5, 109.5),
    )


def degraded_current():
    return scorecards(
        model_name="model",
        predictions=(140.0, 145.0, 150.0),
        observations=(90.0, 95.0, 100.0),
    )


def test_profile_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        DriftDetectionProfile(
            performance_weight=0.20,
            error_weight=0.20,
            bias_weight=0.20,
            direction_weight=0.10,
            calibration_weight=0.10,
        )


def test_profile_thresholds_must_be_ordered() -> None:
    with pytest.raises(ValueError, match="must be ordered"):
        DriftDetectionProfile(
            low_threshold=0.40,
            moderate_threshold=0.20,
        )


def test_empty_scorecards_are_rejected() -> None:
    with pytest.raises(ValueError, match="required"):
        ForecastDriftDetectionEngine().detect((), ())


def test_model_keys_must_match() -> None:
    baseline = stable_baseline()
    current = scorecards(
        model_name="other",
        predictions=(110.0, 111.0, 109.0),
        observations=(109.0, 111.0, 110.0),
    )

    with pytest.raises(ValueError, match="must match"):
        ForecastDriftDetectionEngine().detect(
            baseline,
            current,
        )


def test_stable_model_has_low_drift() -> None:
    report = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        stable_current(),
    )
    signal = report.signals[0]

    assert signal.drift_score < 0.30
    assert signal.severity in (
        DriftSeverity.NONE,
        DriftSeverity.LOW,
    )


def test_degraded_model_has_higher_drift() -> None:
    engine = ForecastDriftDetectionEngine()

    stable = engine.detect(
        stable_baseline(),
        stable_current(),
    ).signals[0]
    degraded = engine.detect(
        stable_baseline(),
        degraded_current(),
    ).signals[0]

    assert degraded.drift_score > stable.drift_score


def test_degraded_model_recommends_action() -> None:
    signal = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        degraded_current(),
    ).signals[0]

    assert signal.recommendation in (
        DriftRecommendation.REDUCE_WEIGHT,
        DriftRecommendation.RETRAIN,
        DriftRecommendation.RETIRE,
    )


def test_regime_change_adds_penalty() -> None:
    engine = ForecastDriftDetectionEngine()

    same = engine.detect(
        stable_baseline(),
        stable_current(),
        baseline_regime="expansion",
        current_regime="expansion",
    ).signals[0]
    changed = engine.detect(
        stable_baseline(),
        stable_current(),
        baseline_regime="expansion",
        current_regime="contraction",
    ).signals[0]

    assert changed.regime_changed is True
    assert changed.drift_score > same.drift_score


def test_signal_contains_all_core_metrics() -> None:
    signal = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        degraded_current(),
    ).signals[0]

    metric_names = {
        item.drift_type.value for item in signal.metrics
    }
    assert metric_names == {
        "performance",
        "error",
        "bias",
        "direction",
        "calibration",
    }


def test_regime_memory_is_created() -> None:
    report = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        stable_current(),
        current_regime="expansion",
    )

    assert len(report.regime_memory) == 1
    assert report.regime_memory[0].regime == "expansion"


def test_prior_history_is_preserved() -> None:
    first = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        stable_current(),
    )
    second = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        degraded_current(),
        prior_history=first.history,
    )

    assert len(second.history.entries) == 2


def test_history_is_json_safe() -> None:
    history = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        stable_current(),
    ).history
    payload = drift_history_to_dict(history)

    assert payload["schema_version"] == "1.0.0"
    assert len(payload["entries"]) == 1


def test_history_json_is_deterministic() -> None:
    history = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        stable_current(),
    ).history

    assert drift_history_to_json(history) == drift_history_to_json(
        history
    )


def test_history_round_trip() -> None:
    history = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        stable_current(),
    ).history
    restored = drift_history_from_dict(
        drift_history_to_dict(history)
    )

    assert restored == history


def test_history_save_and_load(tmp_path) -> None:
    history = ForecastDriftDetectionEngine().detect(
        stable_baseline(),
        stable_current(),
    ).history
    path = tmp_path / "drift_history.json"

    save_drift_history(history, path)
    restored = load_drift_history(path)

    assert restored == history


def test_service_detects_from_archives() -> None:
    baseline_archive = ForecastArchive()
    baseline_archive.extend(
        (
            record(
                forecast_id="base-1",
                model_name="model",
                point_forecast=110.0,
                observed_value=109.0,
            ),
            record(
                forecast_id="base-2",
                model_name="model",
                point_forecast=111.0,
                observed_value=111.0,
            ),
            record(
                forecast_id="base-3",
                model_name="model",
                point_forecast=109.0,
                observed_value=110.0,
            ),
        )
    )
    current_archive = ForecastArchive()
    current_archive.extend(
        (
            record(
                forecast_id="current-1",
                model_name="model",
                point_forecast=140.0,
                observed_value=90.0,
            ),
            record(
                forecast_id="current-2",
                model_name="model",
                point_forecast=145.0,
                observed_value=95.0,
            ),
            record(
                forecast_id="current-3",
                model_name="model",
                point_forecast=150.0,
                observed_value=100.0,
            ),
        )
    )
    service = ForecastDriftDetectionService(
        baseline_archive=baseline_archive,
        current_archive=current_archive,
    )

    report = service.detect(
        performance_profile=PerformanceAnalyticsProfile(
            minimum_sample_size=3
        )
    )

    assert len(report.signals) == 1


def test_service_detects_and_saves(tmp_path) -> None:
    baseline_archive = ForecastArchive()
    current_archive = ForecastArchive()

    for archive, prefix, predictions, observations in (
        (
            baseline_archive,
            "base",
            (110.0, 111.0, 109.0),
            (109.0, 111.0, 110.0),
        ),
        (
            current_archive,
            "current",
            (140.0, 145.0, 150.0),
            (90.0, 95.0, 100.0),
        ),
    ):
        archive.extend(
            tuple(
                record(
                    forecast_id=f"{prefix}-{index}",
                    model_name="model",
                    point_forecast=prediction,
                    observed_value=observation,
                )
                for index, (prediction, observation) in enumerate(
                    zip(predictions, observations),
                    start=1,
                )
            )
        )

    service = ForecastDriftDetectionService(
        baseline_archive=baseline_archive,
        current_archive=current_archive,
    )
    path = tmp_path / "history.json"

    report = service.detect_and_save(
        path,
        performance_profile=PerformanceAnalyticsProfile(
            minimum_sample_size=3
        ),
    )

    assert path.exists()
    assert service.load_history(path) == report.history


def test_detection_is_deterministic_except_history_timestamps() -> None:
    engine = ForecastDriftDetectionEngine()

    first = engine.detect(
        stable_baseline(),
        degraded_current(),
        as_of_date=date(2027, 1, 1),
    )
    second = engine.detect(
        stable_baseline(),
        degraded_current(),
        as_of_date=date(2027, 1, 1),
    )

    first_signal = first.signals[0]
    second_signal = second.signals[0]

    assert first_signal.drift_score == second_signal.drift_score
    assert first_signal.severity == second_signal.severity
    assert first_signal.recommendation == second_signal.recommendation
    assert first_signal.metrics == second_signal.metrics
