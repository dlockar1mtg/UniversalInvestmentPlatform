"""Tests for Phase 4.4.1 forecast outcome tracking."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastInterval,
    ForecastMethod,
    ForecastProvenance,
    ForecastScenario,
    ForecastScenarioResult,
    UniversalForecast,
)
from foundation.intelligence.forecasting.validation import (
    ForecastArchive,
    ForecastOutcome,
    ForecastOutcomeTracker,
    ForecastValidationService,
    OutcomeCompleteness,
    ValidationStatus,
)


def forecast(
    *,
    forecast_id: str = "forecast-001",
    asset_id: str = "TEST",
    point_forecast: float = 110.0,
    direction: ForecastDirection = ForecastDirection.UP,
    interval: ForecastInterval | None = None,
) -> UniversalForecast:
    return UniversalForecast(
        forecast_id=forecast_id,
        asset_id=asset_id,
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        point_forecast=point_forecast,
        currency="USD",
        provenance=ForecastProvenance(
            model_name="validation-model",
            model_version="1.0.0",
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
        ),
        direction=direction,
        expected_return=point_forecast / 100.0 - 1.0,
        confidence_score=0.80,
        interval=interval
        or ForecastInterval(
            coverage=0.95,
            lower=80.0,
            upper=140.0,
        ),
        scenarios=(
            ForecastScenarioResult(
                scenario=ForecastScenario.BEAR,
                target_value=85.0,
                probability=0.20,
            ),
            ForecastScenarioResult(
                scenario=ForecastScenario.BASE,
                target_value=110.0,
                probability=0.60,
            ),
            ForecastScenarioResult(
                scenario=ForecastScenario.BULL,
                target_value=140.0,
                probability=0.20,
            ),
        ),
    )


def outcome(
    *,
    forecast_id: str = "forecast-001",
    asset_id: str = "TEST",
    observed_value: float = 108.0,
    observation_date: date = date(2027, 7, 17),
) -> ForecastOutcome:
    return ForecastOutcome(
        forecast_id=forecast_id,
        asset_id=asset_id,
        observation_date=observation_date,
        observed_value=observed_value,
        completeness=OutcomeCompleteness.COMPLETE,
        realized_volatility=0.22,
        realized_max_drawdown=-0.15,
        source="market-data",
    )


def test_outcome_requires_nonnegative_value() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        outcome(observed_value=-1.0)


def test_outcome_metadata_is_frozen() -> None:
    result = ForecastOutcome(
        forecast_id="f",
        asset_id="a",
        observation_date=date(2027, 1, 1),
        observed_value=100.0,
        metadata={"source_id": "x"},
    )

    with pytest.raises(TypeError):
        result.metadata["source_id"] = "y"


def test_tracker_rejects_forecast_id_mismatch() -> None:
    with pytest.raises(ValueError, match="forecast_id"):
        ForecastOutcomeTracker().validate(
            forecast(),
            outcome(forecast_id="other"),
        )


def test_tracker_rejects_asset_mismatch() -> None:
    with pytest.raises(ValueError, match="asset_id"):
        ForecastOutcomeTracker().validate(
            forecast(),
            outcome(asset_id="OTHER"),
        )


def test_tracker_rejects_early_outcome() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        ForecastOutcomeTracker().validate(
            forecast(),
            outcome(observation_date=date(2027, 7, 16)),
        )


def test_absolute_and_signed_error_are_calculated() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(point_forecast=110.0),
        outcome(observed_value=108.0),
    )

    assert result.signed_error == pytest.approx(2.0)
    assert result.absolute_error == pytest.approx(2.0)


def test_relative_error_is_calculated() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(point_forecast=110.0),
        outcome(observed_value=100.0),
    )

    assert result.relative_error == pytest.approx(0.10)
    assert result.absolute_percentage_error == pytest.approx(0.10)


def test_zero_observed_value_avoids_division() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(point_forecast=10.0),
        outcome(observed_value=0.0),
    )

    assert result.relative_error is None
    assert result.absolute_percentage_error is None


def test_realized_and_forecast_returns_are_calculated() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(point_forecast=110.0),
        outcome(observed_value=120.0),
    )

    assert result.realized_return == pytest.approx(0.20)
    assert result.forecast_return == pytest.approx(0.10)


def test_up_direction_accuracy() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(direction=ForecastDirection.UP),
        outcome(observed_value=108.0),
    )

    assert result.direction_correct is True


def test_down_direction_accuracy() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(
            point_forecast=90.0,
            direction=ForecastDirection.DOWN,
        ),
        outcome(observed_value=85.0),
    )

    assert result.direction_correct is True


def test_flat_direction_accuracy() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(
            point_forecast=100.0,
            direction=ForecastDirection.FLAT,
        ),
        outcome(observed_value=100.0),
    )

    assert result.direction_correct is True


def test_interval_coverage_is_recorded() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(
            interval=ForecastInterval(
                coverage=0.95,
                lower=80.0,
                upper=140.0,
            )
        ),
        outcome(observed_value=130.0),
    )

    assert result.interval_coverage[0.95] is True


def test_interval_miss_is_recorded() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(
            interval=ForecastInterval(
                coverage=0.80,
                lower=90.0,
                upper=125.0,
            )
        ),
        outcome(observed_value=130.0),
    )

    assert result.interval_coverage[0.80] is False


def test_missing_interval_returns_empty_coverage() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(interval=None),
        outcome(observed_value=108.0),
    )

    assert result.interval_coverage == {0.95: True}


def test_nearest_scenario_is_recorded() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(),
        outcome(observed_value=136.0),
    )

    assert result.scenario_hit == ForecastScenario.BULL.value


def test_validation_record_is_validated() -> None:
    result = ForecastOutcomeTracker().validate(
        forecast(),
        outcome(),
    )

    assert result.status is ValidationStatus.VALIDATED
    assert result.validated_at.tzinfo is not None


def test_archive_rejects_duplicate_forecast() -> None:
    archive = ForecastArchive()
    record = ForecastOutcomeTracker().validate(
        forecast(),
        outcome(),
    )
    archive.add(record)

    with pytest.raises(ValueError, match="already archived"):
        archive.add(record)


def test_archive_retrieval_and_filters() -> None:
    archive = ForecastArchive()
    tracker = ForecastOutcomeTracker()

    first = tracker.validate(
        forecast(forecast_id="a", asset_id="AAA"),
        outcome(forecast_id="a", asset_id="AAA"),
    )
    second = tracker.validate(
        forecast(forecast_id="b", asset_id="BBB"),
        outcome(forecast_id="b", asset_id="BBB"),
    )
    archive.extend((second, first))

    assert archive.get("a") == first
    assert archive.contains("b")
    assert archive.by_asset("AAA") == (first,)
    assert len(archive.by_model("validation-model")) == 2
    assert len(archive) == 2


def test_service_validates_and_archives() -> None:
    service = ForecastValidationService()

    record = service.validate_and_archive(
        forecast(),
        outcome(),
    )

    assert service.archive.get("forecast-001") == record


def test_service_batch_is_atomic_for_duplicates() -> None:
    service = ForecastValidationService()
    duplicate_pairs = (
        (forecast(), outcome()),
        (forecast(), outcome()),
    )

    with pytest.raises(ValueError, match="Duplicate forecast ids"):
        service.validate_many(duplicate_pairs)

    assert len(service.archive) == 0


def test_tracking_is_deterministic_except_timestamp() -> None:
    tracker = ForecastOutcomeTracker()

    first = tracker.validate(forecast(), outcome())
    second = tracker.validate(forecast(), outcome())

    assert first.absolute_error == second.absolute_error
    assert first.relative_error == second.relative_error
    assert first.direction_correct == second.direction_correct
    assert first.interval_coverage == second.interval_coverage
    assert first.scenario_hit == second.scenario_hit
