"""Tests for Phase 4.3.1 forecast distribution framework."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json

import pytest

from foundation.intelligence.forecasting.models import ForecastHorizon
from foundation.intelligence.forecasting.probability import (
    DISTRIBUTION_SCHEMA_NAME,
    DISTRIBUTION_SCHEMA_VERSION,
    DistributionFamily,
    DistributionProvenance,
    DistributionSchemaError,
    DistributionStatistics,
    DistributionStatus,
    ForecastConfidenceInterval,
    ForecastDistributionResult,
    ForecastPercentile,
    TailRiskMetrics,
    TailRiskSide,
    distribution_from_dict,
    distribution_to_dict,
    distribution_to_json,
    validate_distribution,
    validate_distribution_payload,
)


def build_distribution() -> ForecastDistributionResult:
    return ForecastDistributionResult(
        distribution_id="distribution-001",
        schema_version=DISTRIBUTION_SCHEMA_VERSION,
        status=DistributionStatus.VALIDATED,
        asset_id="BTC-USD",
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100_000.0,
        currency="USD",
        family=DistributionFamily.MONTE_CARLO,
        statistics=DistributionStatistics(
            mean=118_000.0,
            median=115_000.0,
            variance=400_000_000.0,
            standard_deviation=20_000.0,
            minimum=55_000.0,
            maximum=220_000.0,
            skewness=0.45,
            excess_kurtosis=0.30,
            mode=110_000.0,
            sample_count=10_000,
        ),
        provenance=DistributionProvenance(
            model_name="ensemble-monte-carlo",
            model_version="1.0.0",
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
            source_forecast_ids=("forecast-a", "forecast-b"),
            source_run_id="run-001",
            random_seed=42,
            simulation_count=10_000,
            code_commit="abc1234",
            parameters={"steps": 365},
        ),
        percentiles=(
            ForecastPercentile(0.05, 80_000.0, "p05"),
            ForecastPercentile(0.25, 100_000.0, "p25"),
            ForecastPercentile(0.50, 115_000.0, "p50"),
            ForecastPercentile(0.75, 135_000.0, "p75"),
            ForecastPercentile(0.95, 165_000.0, "p95"),
        ),
        confidence_intervals=(
            ForecastConfidenceInterval(
                lower_probability=0.05,
                upper_probability=0.95,
                lower_value=80_000.0,
                upper_value=165_000.0,
                coverage=0.90,
            ),
            ForecastConfidenceInterval(
                lower_probability=0.25,
                upper_probability=0.75,
                lower_value=100_000.0,
                upper_value=135_000.0,
                coverage=0.50,
            ),
        ),
        tail_risk=(
            TailRiskMetrics(
                confidence_level=0.95,
                side=TailRiskSide.LOWER,
                value_at_risk=-0.20,
                expected_shortfall=-0.28,
                probability_of_loss=0.25,
                probability_of_target_shortfall=0.18,
                target_return=0.05,
            ),
        ),
        probability_above_reference=0.75,
        probability_below_reference=0.25,
        probability_above_target=0.40,
        target_value=140_000.0,
        notes=("Certification fixture",),
        metadata={"regime": "bull"},
    )


def test_percentile_validates_probability() -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        ForecastPercentile(1.1, 100.0)


def test_confidence_interval_validates_coverage() -> None:
    with pytest.raises(ValueError, match="coverage must equal"):
        ForecastConfidenceInterval(
            lower_probability=0.05,
            upper_probability=0.95,
            lower_value=80.0,
            upper_value=120.0,
            coverage=0.80,
        )


def test_distribution_statistics_reject_negative_variance() -> None:
    with pytest.raises(ValueError, match="variance cannot be negative"):
        DistributionStatistics(
            mean=100.0,
            median=100.0,
            variance=-1.0,
            standard_deviation=1.0,
            minimum=80.0,
            maximum=120.0,
        )


def test_distribution_statistics_require_mean_in_range() -> None:
    with pytest.raises(ValueError, match="mean must lie"):
        DistributionStatistics(
            mean=130.0,
            median=100.0,
            variance=1.0,
            standard_deviation=1.0,
            minimum=80.0,
            maximum=120.0,
        )


def test_lower_tail_expected_shortfall_is_more_severe() -> None:
    with pytest.raises(
        ValueError,
        match="expected_shortfall cannot exceed",
    ):
        TailRiskMetrics(
            confidence_level=0.95,
            side=TailRiskSide.LOWER,
            value_at_risk=-0.20,
            expected_shortfall=-0.10,
            probability_of_loss=0.25,
        )


def test_distribution_rejects_nonmonotonic_percentiles() -> None:
    valid = build_distribution()

    with pytest.raises(ValueError, match="nondecreasing"):
        ForecastDistributionResult(
            asset_id=valid.asset_id,
            asset_class=valid.asset_class,
            as_of_date=valid.as_of_date,
            target_date=valid.target_date,
            horizon=valid.horizon,
            reference_value=valid.reference_value,
            currency=valid.currency,
            family=valid.family,
            statistics=valid.statistics,
            provenance=valid.provenance,
            percentiles=(
                ForecastPercentile(0.25, 120.0),
                ForecastPercentile(0.75, 100.0),
            ),
        )


def test_distribution_rejects_duplicate_percentiles() -> None:
    valid = build_distribution()

    with pytest.raises(ValueError, match="must be unique"):
        ForecastDistributionResult(
            asset_id=valid.asset_id,
            asset_class=valid.asset_class,
            as_of_date=valid.as_of_date,
            target_date=valid.target_date,
            horizon=valid.horizon,
            reference_value=valid.reference_value,
            currency=valid.currency,
            family=valid.family,
            statistics=valid.statistics,
            provenance=valid.provenance,
            percentiles=(
                ForecastPercentile(0.50, 100.0),
                ForecastPercentile(0.50, 101.0),
            ),
        )


def test_target_probability_requires_target_value() -> None:
    valid = build_distribution()

    with pytest.raises(ValueError, match="target_value is required"):
        ForecastDistributionResult(
            asset_id=valid.asset_id,
            asset_class=valid.asset_class,
            as_of_date=valid.as_of_date,
            target_date=valid.target_date,
            horizon=valid.horizon,
            reference_value=valid.reference_value,
            currency=valid.currency,
            family=valid.family,
            statistics=valid.statistics,
            provenance=valid.provenance,
            probability_above_target=0.40,
        )


def test_distribution_lookup_helpers() -> None:
    result = build_distribution()

    assert result.percentile(0.50).value == 115_000.0
    assert result.central_interval(0.90).lower_value == 80_000.0


def test_distribution_lookup_helpers_raise_for_missing_values() -> None:
    result = build_distribution()

    with pytest.raises(KeyError):
        result.percentile(0.99)
    with pytest.raises(KeyError):
        result.central_interval(0.80)


def test_distribution_validation_passes_valid_contract() -> None:
    validate_distribution(build_distribution())


def test_distribution_requires_p50_to_match_median() -> None:
    valid = build_distribution()

    bad = ForecastDistributionResult(
        asset_id=valid.asset_id,
        asset_class=valid.asset_class,
        as_of_date=valid.as_of_date,
        target_date=valid.target_date,
        horizon=valid.horizon,
        reference_value=valid.reference_value,
        currency=valid.currency,
        family=valid.family,
        statistics=valid.statistics,
        provenance=valid.provenance,
        percentiles=(
            ForecastPercentile(0.50, 116_000.0),
        ),
    )

    with pytest.raises(
        DistributionSchemaError,
        match="50th percentile",
    ):
        validate_distribution(bad)


def test_distribution_interval_matches_percentiles() -> None:
    valid = build_distribution()

    bad = ForecastDistributionResult(
        asset_id=valid.asset_id,
        asset_class=valid.asset_class,
        as_of_date=valid.as_of_date,
        target_date=valid.target_date,
        horizon=valid.horizon,
        reference_value=valid.reference_value,
        currency=valid.currency,
        family=valid.family,
        statistics=valid.statistics,
        provenance=valid.provenance,
        percentiles=valid.percentiles,
        confidence_intervals=(
            ForecastConfidenceInterval(
                lower_probability=0.05,
                upper_probability=0.95,
                lower_value=81_000.0,
                upper_value=165_000.0,
                coverage=0.90,
            ),
        ),
    )

    with pytest.raises(
        DistributionSchemaError,
        match="lower value is inconsistent",
    ):
        validate_distribution(bad)


def test_distribution_serialization_round_trip() -> None:
    original = build_distribution()

    payload = distribution_to_dict(original)
    restored = distribution_from_dict(payload)

    assert payload["schema_name"] == DISTRIBUTION_SCHEMA_NAME
    assert restored.distribution_id == original.distribution_id
    assert restored.family is DistributionFamily.MONTE_CARLO
    assert restored.statistics.sample_count == 10_000
    assert restored.percentile(0.95).value == 165_000.0
    assert restored.tail_risk[0].side is TailRiskSide.LOWER


def test_distribution_json_is_deterministic_and_safe() -> None:
    result = build_distribution()

    first = distribution_to_json(result)
    second = distribution_to_json(result)
    payload = json.loads(first)

    assert first == second
    assert payload["asset_id"] == "BTC-USD"
    assert payload["provenance"]["parameters"]["steps"] == 365


def test_payload_validation_reports_missing_fields() -> None:
    errors = validate_distribution_payload(
        {"asset_id": "BTC-USD"}
    )

    assert errors
    assert "Missing required field" in errors[0]


def test_payload_rejects_unknown_distribution_family() -> None:
    payload = distribution_to_dict(build_distribution())
    payload["family"] = "unknown-family"

    errors = validate_distribution_payload(payload)

    assert errors
    assert "family must be one of" in errors[0]


def test_provenance_requires_timezone() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        DistributionProvenance(
            model_name="model",
            model_version="1.0.0",
            generated_at=datetime(2026, 7, 17, 12, 0),
        )
