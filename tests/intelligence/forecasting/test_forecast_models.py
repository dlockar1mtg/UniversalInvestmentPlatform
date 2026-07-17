"""Tests for the Phase 4.1 universal forecast model contract."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.models import (
    FORECAST_SCHEMA_NAME,
    FORECAST_SCHEMA_VERSION,
    ForecastDirection,
    ForecastDistribution,
    ForecastHorizon,
    ForecastInterval,
    ForecastMethod,
    ForecastProvenance,
    ForecastScenario,
    ForecastScenarioResult,
    ForecastSchemaError,
    ForecastStatus,
    IntervalType,
    UniversalForecast,
    forecast_from_dict,
    forecast_to_dict,
    validate_forecast,
    validate_forecast_payload,
)


def build_valid_forecast() -> UniversalForecast:
    """Create a fully populated valid forecast for reuse across tests."""

    provenance = ForecastProvenance(
        model_name="universal-baseline",
        model_version="1.0.0",
        method=ForecastMethod.ENSEMBLE,
        generated_at=datetime(2026, 7, 17, 17, 0, tzinfo=timezone.utc),
        training_data_start=date(2021, 7, 17),
        training_data_end=date(2026, 7, 16),
        source_run_id="forecast-run-001",
        source_dataset_ids=("market-daily-v1", "macro-signals-v1"),
        feature_set_version="features-v1",
        code_commit="abc1234",
        parameters={"simulation_count": 2_000},
    )

    return UniversalForecast(
        forecast_id="forecast-001",
        schema_version=FORECAST_SCHEMA_VERSION,
        asset_id="BTC-USD",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100_000.0,
        point_forecast=115_000.0,
        currency="USD",
        provenance=provenance,
        status=ForecastStatus.VALIDATED,
        direction=ForecastDirection.UP,
        confidence_score=0.78,
        expected_return=0.15,
        interval=ForecastInterval(
            lower=82_000.0,
            upper=145_000.0,
            coverage=0.80,
            interval_type=IntervalType.PREDICTION,
        ),
        distribution=ForecastDistribution(
            distribution_name="monte_carlo",
            mean=116_500.0,
            median=114_500.0,
            standard_deviation=18_000.0,
            minimum=60_000.0,
            maximum=190_000.0,
            sample_count=2_000,
            quantiles={
                "p10": 82_000.0,
                "p50": 114_500.0,
                "p90": 145_000.0,
            },
        ),
        scenarios=(
            ForecastScenarioResult(
                scenario=ForecastScenario.BEAR,
                target_value=80_000.0,
                probability=0.20,
                expected_return=-0.20,
                assumptions=("Risk-off environment",),
            ),
            ForecastScenarioResult(
                scenario=ForecastScenario.BASE,
                target_value=115_000.0,
                probability=0.55,
                expected_return=0.15,
                assumptions=("Moderate adoption growth",),
            ),
            ForecastScenarioResult(
                scenario=ForecastScenario.BULL,
                target_value=155_000.0,
                probability=0.25,
                expected_return=0.55,
                assumptions=("Strong institutional demand",),
            ),
        ),
        calibration_score=0.81,
        backtest_run_id="backtest-001",
        notes=("Certification fixture",),
        metadata={"asset_class": "crypto"},
    )


def test_forecast_horizon_approximate_days() -> None:
    assert ForecastHorizon.ONE_DAY.approximate_days == 1
    assert ForecastHorizon.ONE_YEAR.approximate_days == 365
    assert ForecastHorizon.FIVE_YEARS.approximate_days == 1_825


def test_valid_forecast_passes_validation() -> None:
    forecast = build_valid_forecast()
    validate_forecast(forecast)


def test_forecast_serialization_round_trip() -> None:
    original = build_valid_forecast()

    payload = forecast_to_dict(original)
    restored = forecast_from_dict(payload)

    assert payload["schema_name"] == FORECAST_SCHEMA_NAME
    assert payload["schema_version"] == FORECAST_SCHEMA_VERSION
    assert restored.forecast_id == original.forecast_id
    assert restored.asset_id == original.asset_id
    assert restored.horizon is ForecastHorizon.ONE_YEAR
    assert restored.provenance.method is ForecastMethod.ENSEMBLE
    assert restored.interval is not None
    assert restored.interval.lower == 82_000.0
    assert restored.distribution is not None
    assert restored.distribution.sample_count == 2_000
    assert len(restored.scenarios) == 3


def test_serialized_payload_is_json_compatible() -> None:
    import json

    payload = forecast_to_dict(build_valid_forecast())
    encoded = json.dumps(payload)

    assert '"asset_id": "BTC-USD"' in encoded
    assert '"horizon": "1y"' in encoded


def test_interval_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError, match="lower cannot exceed upper"):
        ForecastInterval(lower=120.0, upper=100.0)


def test_confidence_score_rejects_value_above_one() -> None:
    valid = build_valid_forecast()

    with pytest.raises(ValueError, match="confidence_score"):
        UniversalForecast(
            asset_id=valid.asset_id,
            as_of_date=valid.as_of_date,
            target_date=valid.target_date,
            horizon=valid.horizon,
            reference_value=valid.reference_value,
            point_forecast=valid.point_forecast,
            currency=valid.currency,
            provenance=valid.provenance,
            confidence_score=1.01,
        )


def test_target_date_must_follow_as_of_date() -> None:
    valid = build_valid_forecast()

    with pytest.raises(ValueError, match="target_date must be after as_of_date"):
        UniversalForecast(
            asset_id=valid.asset_id,
            as_of_date=date(2026, 7, 17),
            target_date=date(2026, 7, 17),
            horizon=ForecastHorizon.ONE_DAY,
            reference_value=100.0,
            point_forecast=101.0,
            currency="USD",
            provenance=valid.provenance,
        )


def test_duplicate_scenarios_are_rejected() -> None:
    valid = build_valid_forecast()
    duplicate_scenarios = (
        ForecastScenarioResult(
            scenario=ForecastScenario.BASE,
            target_value=110.0,
        ),
        ForecastScenarioResult(
            scenario=ForecastScenario.BASE,
            target_value=120.0,
        ),
    )

    with pytest.raises(ValueError, match="Each scenario may appear only once"):
        UniversalForecast(
            asset_id=valid.asset_id,
            as_of_date=valid.as_of_date,
            target_date=valid.target_date,
            horizon=valid.horizon,
            reference_value=100.0,
            point_forecast=110.0,
            currency="USD",
            provenance=valid.provenance,
            scenarios=duplicate_scenarios,
        )


def test_complete_scenario_probabilities_must_sum_to_one() -> None:
    valid = build_valid_forecast()
    invalid_scenarios = (
        ForecastScenarioResult(
            scenario=ForecastScenario.BEAR,
            target_value=80.0,
            probability=0.20,
        ),
        ForecastScenarioResult(
            scenario=ForecastScenario.BASE,
            target_value=110.0,
            probability=0.50,
        ),
        ForecastScenarioResult(
            scenario=ForecastScenario.BULL,
            target_value=140.0,
            probability=0.20,
        ),
    )

    with pytest.raises(ValueError, match="must sum to 1.0"):
        UniversalForecast(
            asset_id=valid.asset_id,
            as_of_date=valid.as_of_date,
            target_date=valid.target_date,
            horizon=valid.horizon,
            reference_value=100.0,
            point_forecast=110.0,
            currency="USD",
            provenance=valid.provenance,
            scenarios=invalid_scenarios,
        )


def test_expected_return_must_match_values() -> None:
    valid = build_valid_forecast()

    inconsistent = UniversalForecast(
        asset_id=valid.asset_id,
        as_of_date=valid.as_of_date,
        target_date=valid.target_date,
        horizon=valid.horizon,
        reference_value=100.0,
        point_forecast=120.0,
        expected_return=0.10,
        currency="USD",
        provenance=valid.provenance,
    )

    with pytest.raises(ForecastSchemaError, match="expected_return is inconsistent"):
        validate_forecast(inconsistent)


def test_bear_base_bull_values_must_be_ordered() -> None:
    valid = build_valid_forecast()

    incorrectly_ordered = UniversalForecast(
        asset_id=valid.asset_id,
        as_of_date=valid.as_of_date,
        target_date=valid.target_date,
        horizon=valid.horizon,
        reference_value=100.0,
        point_forecast=110.0,
        currency="USD",
        provenance=valid.provenance,
        scenarios=(
            ForecastScenarioResult(
                scenario=ForecastScenario.BEAR,
                target_value=120.0,
                probability=0.20,
            ),
            ForecastScenarioResult(
                scenario=ForecastScenario.BASE,
                target_value=110.0,
                probability=0.50,
            ),
            ForecastScenarioResult(
                scenario=ForecastScenario.BULL,
                target_value=140.0,
                probability=0.30,
            ),
        ),
    )

    with pytest.raises(ForecastSchemaError, match="bear <= base <= bull"):
        validate_forecast(incorrectly_ordered)


def test_payload_validation_reports_missing_fields() -> None:
    errors = validate_forecast_payload({"asset_id": "BTC-USD"})

    assert errors
    assert "Missing required field" in errors[0]


def test_payload_rejects_unknown_horizon() -> None:
    payload = forecast_to_dict(build_valid_forecast())
    payload["horizon"] = "25y"

    errors = validate_forecast_payload(payload)

    assert errors
    assert "horizon must be one of" in errors[0]


def test_naive_generated_at_is_rejected() -> None:
    payload = forecast_to_dict(build_valid_forecast())
    payload["provenance"]["generated_at"] = "2026-07-17T12:00:00"

    errors = validate_forecast_payload(payload)

    assert errors
    assert "must include a timezone" in errors[0]
