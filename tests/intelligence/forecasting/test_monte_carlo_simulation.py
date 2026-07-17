"""Tests for Phase 4.3.2 Monte Carlo simulation engine."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastProvenance,
    UniversalForecast,
)
from foundation.intelligence.forecasting.probability import (
    DistributionFamily,
    DistributionStatus,
    MonteCarloForecastService,
    MonteCarloSimulationEngine,
    MonteCarloSimulationProfile,
    MonteCarloSimulationRequest,
    SimulationProcess,
)


def request(
    *,
    seed: int = 42,
    simulations: int = 2_000,
    steps: int = 12,
    drift: float = 0.08,
    volatility: float = 0.20,
    process: SimulationProcess = (
        SimulationProcess.GEOMETRIC_BROWNIAN_MOTION
    ),
    store_paths: bool = False,
    floor_value: float | None = 0.0,
    target_value: float | None = 120.0,
) -> MonteCarloSimulationRequest:
    return MonteCarloSimulationRequest(
        asset_id="TEST",
        asset_class="equity",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        currency="USD",
        model_name="test-model",
        model_version="1.0.0",
        target_value=target_value,
        profile=MonteCarloSimulationProfile(
            simulation_count=simulations,
            steps=steps,
            annual_drift=drift,
            annual_volatility=volatility,
            process=process,
            random_seed=seed,
            store_paths=store_paths,
            maximum_stored_paths=5,
            floor_value=floor_value,
        ),
    )


def forecast() -> UniversalForecast:
    return UniversalForecast(
        forecast_id="forecast-001",
        asset_id="TEST",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        point_forecast=108.0,
        currency="USD",
        provenance=ForecastProvenance(
            model_name="service-model",
            model_version="1.0.0",
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
        ),
        direction=ForecastDirection.UP,
        expected_return=0.08,
        confidence_score=0.80,
    )


def test_profile_requires_positive_simulation_count() -> None:
    with pytest.raises(ValueError, match="simulation_count"):
        MonteCarloSimulationProfile(simulation_count=0)


def test_profile_requires_median_percentile() -> None:
    with pytest.raises(ValueError, match="must include 0.50"):
        MonteCarloSimulationProfile(
            percentile_levels=(0.05, 0.95)
        )


def test_request_requires_positive_reference_value() -> None:
    valid = request()
    with pytest.raises(ValueError, match="must be positive"):
        MonteCarloSimulationRequest(
            asset_id=valid.asset_id,
            asset_class=valid.asset_class,
            as_of_date=valid.as_of_date,
            target_date=valid.target_date,
            horizon=valid.horizon,
            reference_value=0.0,
            currency=valid.currency,
            model_name=valid.model_name,
            model_version=valid.model_version,
            profile=valid.profile,
        )


def test_seeded_simulation_is_deterministic() -> None:
    engine = MonteCarloSimulationEngine()

    first = engine.simulate(request(seed=99))
    second = engine.simulate(request(seed=99))

    assert first.terminal_values == second.terminal_values
    assert (
        first.distribution.statistics.mean
        == pytest.approx(second.distribution.statistics.mean)
    )


def test_different_seeds_produce_different_terminal_values() -> None:
    engine = MonteCarloSimulationEngine()

    first = engine.simulate(request(seed=1))
    second = engine.simulate(request(seed=2))

    assert first.terminal_values != second.terminal_values


def test_zero_volatility_matches_deterministic_gbm_value() -> None:
    result = MonteCarloSimulationEngine().simulate(
        request(
            simulations=100,
            steps=12,
            drift=0.10,
            volatility=0.0,
        )
    )

    expected = 100.0 * __import__("math").exp(0.10)
    assert result.distribution.statistics.mean == pytest.approx(
        expected,
        rel=1e-3,
    )
    assert result.distribution.statistics.standard_deviation == pytest.approx(
        0.0,
        abs=1e-10,
    )


def test_arithmetic_process_is_supported() -> None:
    result = MonteCarloSimulationEngine().simulate(
        request(
            process=SimulationProcess.ARITHMETIC_BROWNIAN_MOTION
        )
    )

    assert len(result.terminal_values) == 2_000
    assert result.distribution.family is DistributionFamily.MONTE_CARLO


def test_distribution_contains_expected_percentiles() -> None:
    result = MonteCarloSimulationEngine().simulate(request())

    probabilities = {
        item.probability for item in result.distribution.percentiles
    }
    assert probabilities == {0.05, 0.25, 0.50, 0.75, 0.95}
    assert result.distribution.percentile(0.50).value == pytest.approx(
        result.distribution.statistics.median
    )


def test_distribution_contains_confidence_intervals() -> None:
    result = MonteCarloSimulationEngine().simulate(request())

    assert result.distribution.central_interval(0.90).coverage == 0.90
    assert result.distribution.central_interval(0.50).coverage == 0.50


def test_tail_risk_contains_var_and_expected_shortfall() -> None:
    result = MonteCarloSimulationEngine().simulate(request())
    risk = result.distribution.tail_risk[0]

    assert risk.confidence_level == 0.95
    assert risk.expected_shortfall <= risk.value_at_risk
    assert 0.0 <= risk.probability_of_loss <= 1.0
    assert risk.probability_of_target_shortfall is not None


def test_probability_metrics_are_bounded() -> None:
    distribution = MonteCarloSimulationEngine().simulate(
        request()
    ).distribution

    assert 0.0 <= distribution.probability_above_reference <= 1.0
    assert 0.0 <= distribution.probability_below_reference <= 1.0
    assert 0.0 <= distribution.probability_above_target <= 1.0


def test_simulation_provenance_records_reproducibility() -> None:
    result = MonteCarloSimulationEngine().simulate(
        request(seed=123, simulations=500, steps=24)
    )
    provenance = result.distribution.provenance

    assert provenance.random_seed == 123
    assert provenance.simulation_count == 500
    assert provenance.parameters["steps"] == 24
    assert provenance.parameters["process"] == (
        SimulationProcess.GEOMETRIC_BROWNIAN_MOTION.value
    )


def test_diagnostics_match_execution() -> None:
    result = MonteCarloSimulationEngine().simulate(
        request(simulations=500, steps=10)
    )

    assert result.diagnostics.simulation_count == 500
    assert result.diagnostics.steps == 10
    assert result.diagnostics.invalid_value_count == 0
    assert result.diagnostics.terminal_minimum <= (
        result.diagnostics.terminal_maximum
    )


def test_paths_are_not_stored_by_default() -> None:
    result = MonteCarloSimulationEngine().simulate(request())

    assert result.stored_paths == ()
    assert result.diagnostics.stored_path_count == 0


def test_path_storage_respects_maximum() -> None:
    result = MonteCarloSimulationEngine().simulate(
        request(store_paths=True, simulations=50, steps=8)
    )

    assert len(result.stored_paths) == 5
    assert len(result.stored_paths[0]) == 8
    assert result.diagnostics.stored_path_count == 5


def test_floor_clips_negative_arithmetic_values() -> None:
    result = MonteCarloSimulationEngine().simulate(
        request(
            simulations=500,
            steps=3,
            drift=-2.0,
            volatility=0.0,
            process=SimulationProcess.ARITHMETIC_BROWNIAN_MOTION,
            floor_value=0.0,
        )
    )

    assert min(result.terminal_values) == 0.0
    assert result.diagnostics.clipped_value_count > 0


def test_distribution_is_validated() -> None:
    result = MonteCarloSimulationEngine().simulate(request())

    assert result.distribution.status is DistributionStatus.VALIDATED
    assert result.distribution.statistics.sample_count == 2_000


def test_service_builds_request_from_universal_forecast() -> None:
    result = MonteCarloForecastService().simulate_forecast(
        forecast(),
        asset_class="equity",
        profile=MonteCarloSimulationProfile(
            simulation_count=500,
            steps=12,
            annual_drift=0.08,
            annual_volatility=0.20,
            random_seed=7,
        ),
        target_value=120.0,
        source_run_id="run-001",
    )

    distribution = result.distribution
    assert distribution.asset_id == "TEST"
    assert distribution.asset_class == "equity"
    assert distribution.provenance.source_forecast_ids == (
        "forecast-001",
    )
    assert distribution.provenance.source_run_id == "run-001"


def test_service_uses_forecast_expected_return_by_default() -> None:
    result = MonteCarloForecastService().simulate_forecast(
        forecast(),
        asset_class="equity",
    )

    assert result.distribution.provenance.parameters[
        "annual_drift"
    ] == pytest.approx(0.08)
