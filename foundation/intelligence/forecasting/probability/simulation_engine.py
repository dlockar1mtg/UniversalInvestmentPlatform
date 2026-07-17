"""Deterministic Monte Carlo simulation engine."""

from __future__ import annotations

from datetime import datetime, timezone
from math import exp, isfinite, sqrt
from statistics import mean, median, pvariance, pstdev
from time import perf_counter

import numpy as np

from .distribution_enums import (
    DistributionFamily,
    DistributionStatus,
    TailRiskSide,
)
from .distribution_models import (
    DistributionProvenance,
    DistributionStatistics,
    ForecastConfidenceInterval,
    ForecastDistributionResult,
    ForecastPercentile,
    TailRiskMetrics,
)
from .simulation_contracts import (
    MonteCarloDiagnostics,
    MonteCarloSimulationRequest,
    MonteCarloSimulationResult,
    SimulationProcess,
)


class MonteCarloSimulationEngine:
    """Generate terminal-value distributions from seeded stochastic paths."""

    def simulate(
        self,
        request: MonteCarloSimulationRequest,
    ) -> MonteCarloSimulationResult:
        started = perf_counter()
        profile = request.profile
        rng = np.random.default_rng(profile.random_seed)

        dt = self._year_fraction(request)
        step_dt = dt / profile.steps
        shocks = rng.standard_normal(
            size=(profile.simulation_count, profile.steps)
        )

        if profile.process is SimulationProcess.GEOMETRIC_BROWNIAN_MOTION:
            paths = self._simulate_gbm(
                reference_value=request.reference_value,
                shocks=shocks,
                annual_drift=profile.annual_drift,
                annual_volatility=profile.annual_volatility,
                step_dt=step_dt,
            )
        elif profile.process is SimulationProcess.ARITHMETIC_BROWNIAN_MOTION:
            paths = self._simulate_abm(
                reference_value=request.reference_value,
                shocks=shocks,
                annual_drift=profile.annual_drift,
                annual_volatility=profile.annual_volatility,
                step_dt=step_dt,
            )
        else:
            raise ValueError(
                f"Unsupported simulation process: {profile.process}"
            )

        invalid_mask = ~np.isfinite(paths)
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            raise ValueError(
                "Simulation produced non-finite path values."
            )

        clipped_count = 0
        if profile.floor_value is not None:
            clipped_mask = paths < profile.floor_value
            clipped_count = int(clipped_mask.sum())
            if clipped_count:
                paths = np.maximum(paths, profile.floor_value)

        terminal = paths[:, -1]
        terminal_values = tuple(float(value) for value in terminal.tolist())

        distribution = self._build_distribution(
            request=request,
            terminal=terminal,
        )
        stored_paths = self._stored_paths(paths, request)
        runtime = perf_counter() - started

        diagnostics = MonteCarloDiagnostics(
            simulation_count=profile.simulation_count,
            steps=profile.steps,
            random_seed=profile.random_seed,
            clipped_value_count=clipped_count,
            invalid_value_count=invalid_count,
            terminal_minimum=float(np.min(terminal)),
            terminal_maximum=float(np.max(terminal)),
            runtime_seconds=runtime,
            stored_path_count=len(stored_paths),
        )
        return MonteCarloSimulationResult(
            distribution=distribution,
            diagnostics=diagnostics,
            terminal_values=terminal_values,
            stored_paths=stored_paths,
        )

    @staticmethod
    def _year_fraction(
        request: MonteCarloSimulationRequest,
    ) -> float:
        days = (request.target_date - request.as_of_date).days
        return days / 365.25

    @staticmethod
    def _simulate_gbm(
        *,
        reference_value: float,
        shocks: np.ndarray,
        annual_drift: float,
        annual_volatility: float,
        step_dt: float,
    ) -> np.ndarray:
        drift_term = (
            annual_drift - 0.5 * annual_volatility**2
        ) * step_dt
        diffusion = annual_volatility * sqrt(step_dt) * shocks
        log_returns = drift_term + diffusion
        cumulative = np.cumsum(log_returns, axis=1)
        return reference_value * np.exp(cumulative)

    @staticmethod
    def _simulate_abm(
        *,
        reference_value: float,
        shocks: np.ndarray,
        annual_drift: float,
        annual_volatility: float,
        step_dt: float,
    ) -> np.ndarray:
        increments = (
            reference_value * annual_drift * step_dt
            + reference_value
            * annual_volatility
            * sqrt(step_dt)
            * shocks
        )
        return reference_value + np.cumsum(increments, axis=1)

    def _build_distribution(
        self,
        *,
        request: MonteCarloSimulationRequest,
        terminal: np.ndarray,
    ) -> ForecastDistributionResult:
        profile = request.profile
        percentiles = tuple(
            ForecastPercentile(
                probability=level,
                value=float(np.quantile(terminal, level)),
                label=f"p{round(level * 100):02d}",
            )
            for level in sorted(profile.percentile_levels)
        )
        percentile_map = {
            item.probability: item.value for item in percentiles
        }

        intervals = []
        for coverage in sorted(profile.interval_coverages):
            lower_probability = (1.0 - coverage) / 2.0
            upper_probability = 1.0 - lower_probability
            lower_value = float(np.quantile(terminal, lower_probability))
            upper_value = float(np.quantile(terminal, upper_probability))
            intervals.append(
                ForecastConfidenceInterval(
                    lower_probability=lower_probability,
                    upper_probability=upper_probability,
                    lower_value=lower_value,
                    upper_value=upper_value,
                    coverage=coverage,
                )
            )

        returns = terminal / request.reference_value - 1.0
        tail_risk = tuple(
            self._tail_risk(
                returns=returns,
                confidence_level=level,
                target_value=request.target_value,
                reference_value=request.reference_value,
            )
            for level in sorted(profile.var_confidence_levels)
        )

        distribution_statistics = self._statistics(terminal)
        probability_above_reference = float(
            np.mean(terminal > request.reference_value)
        )
        probability_below_reference = float(
            np.mean(terminal < request.reference_value)
        )
        probability_above_target = (
            None
            if request.target_value is None
            else float(np.mean(terminal > request.target_value))
        )

        return ForecastDistributionResult(
            asset_id=request.asset_id,
            asset_class=request.asset_class,
            as_of_date=request.as_of_date,
            target_date=request.target_date,
            horizon=request.horizon,
            reference_value=request.reference_value,
            currency=request.currency,
            family=DistributionFamily.MONTE_CARLO,
            statistics=distribution_statistics,
            provenance=DistributionProvenance(
                model_name=request.model_name,
                model_version=request.model_version,
                generated_at=datetime.now(timezone.utc),
                source_forecast_ids=request.source_forecast_ids,
                source_run_id=request.source_run_id,
                random_seed=profile.random_seed,
                simulation_count=profile.simulation_count,
                parameters={
                    "process": profile.process.value,
                    "steps": profile.steps,
                    "annual_drift": profile.annual_drift,
                    "annual_volatility": profile.annual_volatility,
                    "floor_value": profile.floor_value,
                },
            ),
            status=DistributionStatus.VALIDATED,
            percentiles=percentiles,
            confidence_intervals=tuple(intervals),
            tail_risk=tail_risk,
            probability_above_reference=probability_above_reference,
            probability_below_reference=probability_below_reference,
            probability_above_target=probability_above_target,
            target_value=request.target_value,
            metadata={
                **dict(request.metadata),
                "median_percentile_value": percentile_map[0.50],
            },
        )

    @staticmethod
    def _statistics(
        terminal: np.ndarray,
    ) -> DistributionStatistics:
        values = terminal.astype(float)
        mu = float(np.mean(values))
        med = float(np.median(values))
        variance = float(np.var(values))
        standard_deviation = float(np.std(values))
        minimum = float(np.min(values))
        maximum = float(np.max(values))

        if standard_deviation == 0:
            skewness = 0.0
            excess_kurtosis = 0.0
        else:
            centered = (values - mu) / standard_deviation
            skewness = float(np.mean(centered**3))
            excess_kurtosis = float(np.mean(centered**4) - 3.0)

        return DistributionStatistics(
            mean=mu,
            median=med,
            variance=variance,
            standard_deviation=standard_deviation,
            minimum=minimum,
            maximum=maximum,
            skewness=skewness,
            excess_kurtosis=excess_kurtosis,
            mode=None,
            sample_count=len(values),
        )

    @staticmethod
    def _tail_risk(
        *,
        returns: np.ndarray,
        confidence_level: float,
        target_value: float | None,
        reference_value: float,
    ) -> TailRiskMetrics:
        alpha = 1.0 - confidence_level
        value_at_risk = float(np.quantile(returns, alpha))
        tail = returns[returns <= value_at_risk]
        expected_shortfall = (
            value_at_risk
            if tail.size == 0
            else float(np.mean(tail))
        )
        probability_of_loss = float(np.mean(returns < 0.0))

        target_return = (
            None
            if target_value is None
            else target_value / reference_value - 1.0
        )
        probability_of_target_shortfall = (
            None
            if target_return is None
            else float(np.mean(returns < target_return))
        )

        return TailRiskMetrics(
            confidence_level=confidence_level,
            side=TailRiskSide.LOWER,
            value_at_risk=value_at_risk,
            expected_shortfall=expected_shortfall,
            probability_of_loss=probability_of_loss,
            probability_of_target_shortfall=(
                probability_of_target_shortfall
            ),
            target_return=target_return,
        )

    @staticmethod
    def _stored_paths(
        paths: np.ndarray,
        request: MonteCarloSimulationRequest,
    ) -> tuple[tuple[float, ...], ...]:
        profile = request.profile
        if not profile.store_paths:
            return ()
        count = min(
            profile.simulation_count,
            profile.maximum_stored_paths,
        )
        return tuple(
            tuple(float(value) for value in row.tolist())
            for row in paths[:count]
        )
