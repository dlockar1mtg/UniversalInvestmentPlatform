"""Bayesian forecast updating engine."""

from __future__ import annotations

from datetime import datetime, timezone
from math import erf, exp, pi, sqrt

import numpy as np

from .bayesian_contracts import (
    BayesianUpdateDiagnostics,
    BayesianUpdateFamily,
    BayesianUpdateRequest,
    BayesianUpdateResult,
    BayesianUpdateStatus,
)
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


class BayesianForecastUpdateEngine:
    """Apply conjugate Bayesian updates and emit canonical distributions."""

    def update(
        self,
        request: BayesianUpdateRequest,
    ) -> BayesianUpdateResult:
        if request.family is BayesianUpdateFamily.NORMAL_NORMAL:
            return self._update_normal(request)
        if request.family is BayesianUpdateFamily.BETA_BINOMIAL:
            return self._update_beta(request)
        raise ValueError(f"Unsupported Bayesian family: {request.family}")

    def _update_normal(
        self,
        request: BayesianUpdateRequest,
    ) -> BayesianUpdateResult:
        prior = request.normal_prior
        assert prior is not None

        prior_precision = 1.0 / prior.variance
        posterior_precision = prior_precision
        weighted_sum = prior_precision * prior.mean
        effective_sample_size = 0.0
        evidence_precision = 0.0

        for item in request.normal_evidence:
            scaled_n = item.sample_size * item.weight
            precision = scaled_n / item.observation_variance
            posterior_precision += precision
            weighted_sum += precision * item.sample_mean
            evidence_precision += precision
            effective_sample_size += scaled_n

        posterior_mean = weighted_sum / posterior_precision
        posterior_variance = 1.0 / posterior_precision
        posterior_std = sqrt(posterior_variance)

        status = (
            BayesianUpdateStatus.UPDATED
            if request.normal_evidence
            else BayesianUpdateStatus.NO_EVIDENCE
        )
        shift = posterior_mean - prior.mean

        percentiles = tuple(
            ForecastPercentile(
                probability=probability,
                value=self._normal_quantile(
                    probability,
                    posterior_mean,
                    posterior_std,
                ),
                label=f"p{round(probability * 100):02d}",
            )
            for probability in (0.05, 0.25, 0.50, 0.75, 0.95)
        )
        intervals = (
            self._normal_interval(0.50, posterior_mean, posterior_std),
            self._normal_interval(0.90, posterior_mean, posterior_std),
        )

        probability_above_reference = 1.0 - self._normal_cdf(
            request.reference_value,
            posterior_mean,
            posterior_std,
        )
        probability_below_reference = self._normal_cdf(
            request.reference_value,
            posterior_mean,
            posterior_std,
        )
        probability_above_target = (
            None
            if request.target_value is None
            else 1.0
            - self._normal_cdf(
                request.target_value,
                posterior_mean,
                posterior_std,
            )
        )

        return_distribution = self._normal_return_distribution(
            mean_value=posterior_mean,
            std_value=posterior_std,
            reference_value=request.reference_value,
        )
        tail_risk = (
            self._normal_tail_risk(
                return_mean=return_distribution[0],
                return_std=return_distribution[1],
                target_value=request.target_value,
                reference_value=request.reference_value,
            ),
        )

        distribution = ForecastDistributionResult(
            asset_id=request.asset_id,
            asset_class=request.asset_class,
            as_of_date=request.as_of_date,
            target_date=request.target_date,
            horizon=request.horizon,
            reference_value=request.reference_value,
            currency=request.currency,
            family=DistributionFamily.BAYESIAN_POSTERIOR,
            statistics=DistributionStatistics(
                mean=posterior_mean,
                median=posterior_mean,
                variance=posterior_variance,
                standard_deviation=posterior_std,
                minimum=self._normal_quantile(
                    0.000001,
                    posterior_mean,
                    posterior_std,
                ),
                maximum=self._normal_quantile(
                    0.999999,
                    posterior_mean,
                    posterior_std,
                ),
                skewness=0.0,
                excess_kurtosis=0.0,
                mode=posterior_mean,
                sample_count=(
                    None
                    if not request.normal_evidence
                    else int(round(effective_sample_size))
                ),
            ),
            provenance=DistributionProvenance(
                model_name=request.model_name,
                model_version=request.model_version,
                generated_at=datetime.now(timezone.utc),
                parameters={
                    "family": request.family.value,
                    "prior_mean": prior.mean,
                    "prior_variance": prior.variance,
                    "posterior_mean": posterior_mean,
                    "posterior_variance": posterior_variance,
                },
            ),
            status=DistributionStatus.VALIDATED,
            percentiles=percentiles,
            confidence_intervals=intervals,
            tail_risk=tail_risk,
            probability_above_reference=probability_above_reference,
            probability_below_reference=probability_below_reference,
            probability_above_target=probability_above_target,
            target_value=request.target_value,
            metadata=dict(request.metadata),
        )

        diagnostics = BayesianUpdateDiagnostics(
            family=request.family,
            status=status,
            evidence_count=len(request.normal_evidence),
            effective_sample_size=effective_sample_size,
            prior_weight=prior_precision,
            evidence_weight=evidence_precision,
            posterior_shift=shift,
            explanation=self._normal_explanation(
                status=status,
                prior_mean=prior.mean,
                posterior_mean=posterior_mean,
                posterior_std=posterior_std,
            ),
            metrics={
                "posterior_precision": posterior_precision,
                "posterior_variance": posterior_variance,
            },
        )
        return BayesianUpdateResult(
            distribution=distribution,
            diagnostics=diagnostics,
            posterior_parameters={
                "mean": posterior_mean,
                "variance": posterior_variance,
                "standard_deviation": posterior_std,
            },
        )

    def _update_beta(
        self,
        request: BayesianUpdateRequest,
    ) -> BayesianUpdateResult:
        prior = request.beta_prior
        assert prior is not None

        weighted_successes = sum(
            item.successes * item.weight
            for item in request.binomial_evidence
        )
        weighted_failures = sum(
            (item.trials - item.successes) * item.weight
            for item in request.binomial_evidence
        )
        effective_sample_size = weighted_successes + weighted_failures

        posterior_alpha = prior.alpha + weighted_successes
        posterior_beta = prior.beta + weighted_failures
        posterior_total = posterior_alpha + posterior_beta
        posterior_mean = posterior_alpha / posterior_total
        posterior_variance = (
            posterior_alpha
            * posterior_beta
            / (
                posterior_total**2
                * (posterior_total + 1.0)
            )
        )
        posterior_std = sqrt(posterior_variance)
        mode = (
            (posterior_alpha - 1.0)
            / (posterior_total - 2.0)
            if posterior_alpha > 1.0 and posterior_beta > 1.0
            else posterior_mean
        )

        status = (
            BayesianUpdateStatus.UPDATED
            if request.binomial_evidence
            else BayesianUpdateStatus.NO_EVIDENCE
        )
        shift = posterior_mean - prior.mean

        grid = np.linspace(0.0, 1.0, 20_001)
        density = self._beta_density(
            grid,
            posterior_alpha,
            posterior_beta,
        )
        cumulative = np.cumsum(density)
        cumulative /= cumulative[-1]

        percentile_levels = (0.05, 0.25, 0.50, 0.75, 0.95)
        percentile_values = {
            probability: float(
                grid[np.searchsorted(cumulative, probability)]
            )
            for probability in percentile_levels
        }
        percentiles = tuple(
            ForecastPercentile(
                probability=probability,
                value=percentile_values[probability],
                label=f"p{round(probability * 100):02d}",
            )
            for probability in percentile_levels
        )

        intervals = (
            ForecastConfidenceInterval(
                lower_probability=0.25,
                upper_probability=0.75,
                lower_value=percentile_values[0.25],
                upper_value=percentile_values[0.75],
                coverage=0.50,
            ),
            ForecastConfidenceInterval(
                lower_probability=0.05,
                upper_probability=0.95,
                lower_value=percentile_values[0.05],
                upper_value=percentile_values[0.95],
                coverage=0.90,
            ),
        )

        probability_above_reference = (
            1.0
            if request.reference_value <= 0.0
            else 0.0
            if request.reference_value >= 1.0
            else 1.0
            - self._beta_cdf_from_grid(
                request.reference_value,
                grid,
                cumulative,
            )
        )
        probability_below_reference = 1.0 - probability_above_reference
        probability_above_target = (
            None
            if request.target_value is None
            else 1.0
            - self._beta_cdf_from_grid(
                request.target_value,
                grid,
                cumulative,
            )
        )

        tail_risk = (
            self._beta_tail_risk(
                posterior_alpha=posterior_alpha,
                posterior_beta=posterior_beta,
                reference_value=request.reference_value,
                target_value=request.target_value,
                grid=grid,
                cumulative=cumulative,
            ),
        )

        distribution = ForecastDistributionResult(
            asset_id=request.asset_id,
            asset_class=request.asset_class,
            as_of_date=request.as_of_date,
            target_date=request.target_date,
            horizon=request.horizon,
            reference_value=request.reference_value,
            currency=request.currency,
            family=DistributionFamily.BAYESIAN_POSTERIOR,
            statistics=DistributionStatistics(
                mean=posterior_mean,
                median=percentile_values[0.50],
                variance=posterior_variance,
                standard_deviation=posterior_std,
                minimum=0.0,
                maximum=1.0,
                skewness=self._beta_skewness(
                    posterior_alpha,
                    posterior_beta,
                ),
                excess_kurtosis=self._beta_excess_kurtosis(
                    posterior_alpha,
                    posterior_beta,
                ),
                mode=mode,
                sample_count=(
                    None
                    if not request.binomial_evidence
                    else int(round(effective_sample_size))
                ),
            ),
            provenance=DistributionProvenance(
                model_name=request.model_name,
                model_version=request.model_version,
                generated_at=datetime.now(timezone.utc),
                parameters={
                    "family": request.family.value,
                    "prior_alpha": prior.alpha,
                    "prior_beta": prior.beta,
                    "posterior_alpha": posterior_alpha,
                    "posterior_beta": posterior_beta,
                },
            ),
            status=DistributionStatus.VALIDATED,
            percentiles=percentiles,
            confidence_intervals=intervals,
            tail_risk=tail_risk,
            probability_above_reference=probability_above_reference,
            probability_below_reference=probability_below_reference,
            probability_above_target=probability_above_target,
            target_value=request.target_value,
            metadata=dict(request.metadata),
        )

        diagnostics = BayesianUpdateDiagnostics(
            family=request.family,
            status=status,
            evidence_count=len(request.binomial_evidence),
            effective_sample_size=effective_sample_size,
            prior_weight=prior.alpha + prior.beta,
            evidence_weight=effective_sample_size,
            posterior_shift=shift,
            explanation=self._beta_explanation(
                status=status,
                prior_mean=prior.mean,
                posterior_mean=posterior_mean,
            ),
            metrics={
                "posterior_alpha": posterior_alpha,
                "posterior_beta": posterior_beta,
                "posterior_variance": posterior_variance,
            },
        )
        return BayesianUpdateResult(
            distribution=distribution,
            diagnostics=diagnostics,
            posterior_parameters={
                "alpha": posterior_alpha,
                "beta": posterior_beta,
                "mean": posterior_mean,
                "variance": posterior_variance,
            },
        )

    @staticmethod
    def _normal_cdf(
        value: float,
        mean_value: float,
        std_value: float,
    ) -> float:
        if std_value == 0:
            return 0.0 if value < mean_value else 1.0
        z = (value - mean_value) / (std_value * sqrt(2.0))
        return 0.5 * (1.0 + erf(z))

    @staticmethod
    def _normal_quantile(
        probability: float,
        mean_value: float,
        std_value: float,
    ) -> float:
        if std_value == 0:
            return mean_value
        # Acklam inverse-normal approximation.
        a = (
            -39.6968302866538,
            220.946098424521,
            -275.928510446969,
            138.357751867269,
            -30.6647980661472,
            2.50662827745924,
        )
        b = (
            -54.4760987982241,
            161.585836858041,
            -155.698979859887,
            66.8013118877197,
            -13.2806815528857,
        )
        c = (
            -0.00778489400243029,
            -0.322396458041136,
            -2.40075827716184,
            -2.54973253934373,
            4.37466414146497,
            2.93816398269878,
        )
        d = (
            0.00778469570904146,
            0.32246712907004,
            2.445134137143,
            3.75440866190742,
        )
        p_low = 0.02425
        p_high = 1.0 - p_low

        if probability <= 0.0:
            return float("-inf")
        if probability >= 1.0:
            return float("inf")
        if probability < p_low:
            q = sqrt(-2.0 * np.log(probability))
            z = (
                (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q
                   + c[4]) * q + c[5])
                / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
            )
        elif probability <= p_high:
            q = probability - 0.5
            r = q * q
            z = (
                (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r
                   + a[4]) * r + a[5]) * q
                / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r
                     + b[4]) * r + 1.0)
            )
        else:
            q = sqrt(-2.0 * np.log(1.0 - probability))
            z = -(
                (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q
                   + c[4]) * q + c[5])
                / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
            )
        return mean_value + z * std_value

    def _normal_interval(
        self,
        coverage: float,
        mean_value: float,
        std_value: float,
    ) -> ForecastConfidenceInterval:
        lower_probability = (1.0 - coverage) / 2.0
        upper_probability = 1.0 - lower_probability
        return ForecastConfidenceInterval(
            lower_probability=lower_probability,
            upper_probability=upper_probability,
            lower_value=self._normal_quantile(
                lower_probability,
                mean_value,
                std_value,
            ),
            upper_value=self._normal_quantile(
                upper_probability,
                mean_value,
                std_value,
            ),
            coverage=coverage,
        )

    @staticmethod
    def _normal_return_distribution(
        *,
        mean_value: float,
        std_value: float,
        reference_value: float,
    ) -> tuple[float, float]:
        return (
            mean_value / reference_value - 1.0,
            std_value / reference_value,
        )

    def _normal_tail_risk(
        self,
        *,
        return_mean: float,
        return_std: float,
        target_value: float | None,
        reference_value: float,
    ) -> TailRiskMetrics:
        value_at_risk = self._normal_quantile(
            0.05,
            return_mean,
            return_std,
        )
        z = (value_at_risk - return_mean) / return_std if return_std else 0.0
        phi = exp(-0.5 * z * z) / sqrt(2.0 * pi)
        expected_shortfall = (
            value_at_risk
            if return_std == 0
            else return_mean - return_std * phi / 0.05
        )
        probability_of_loss = self._normal_cdf(
            0.0,
            return_mean,
            return_std,
        )
        target_return = (
            None
            if target_value is None
            else target_value / reference_value - 1.0
        )
        probability_of_target_shortfall = (
            None
            if target_return is None
            else self._normal_cdf(
                target_return,
                return_mean,
                return_std,
            )
        )
        return TailRiskMetrics(
            confidence_level=0.95,
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
    def _beta_density(
        grid: np.ndarray,
        alpha: float,
        beta: float,
    ) -> np.ndarray:
        clipped = np.clip(grid, 1e-12, 1.0 - 1e-12)
        log_density = (
            (alpha - 1.0) * np.log(clipped)
            + (beta - 1.0) * np.log(1.0 - clipped)
        )
        log_density -= np.max(log_density)
        return np.exp(log_density)

    @staticmethod
    def _beta_cdf_from_grid(
        value: float,
        grid: np.ndarray,
        cumulative: np.ndarray,
    ) -> float:
        if value <= 0.0:
            return 0.0
        if value >= 1.0:
            return 1.0
        index = np.searchsorted(grid, value)
        index = min(index, len(cumulative) - 1)
        return float(cumulative[index])

    @staticmethod
    def _beta_skewness(alpha: float, beta: float) -> float:
        numerator = 2.0 * (beta - alpha) * sqrt(alpha + beta + 1.0)
        denominator = (
            (alpha + beta + 2.0) * sqrt(alpha * beta)
        )
        return numerator / denominator

    @staticmethod
    def _beta_excess_kurtosis(alpha: float, beta: float) -> float:
        numerator = 6.0 * (
            (alpha - beta) ** 2 * (alpha + beta + 1.0)
            - alpha * beta * (alpha + beta + 2.0)
        )
        denominator = (
            alpha
            * beta
            * (alpha + beta + 2.0)
            * (alpha + beta + 3.0)
        )
        return numerator / denominator

    def _beta_tail_risk(
        self,
        *,
        posterior_alpha: float,
        posterior_beta: float,
        reference_value: float,
        target_value: float | None,
        grid: np.ndarray,
        cumulative: np.ndarray,
    ) -> TailRiskMetrics:
        q05_index = np.searchsorted(cumulative, 0.05)
        q05 = float(grid[min(q05_index, len(grid) - 1)])
        returns = grid / reference_value - 1.0
        value_at_risk = q05 / reference_value - 1.0

        density = self._beta_density(
            grid,
            posterior_alpha,
            posterior_beta,
        )
        mask = grid <= q05
        expected_value_tail = float(
            np.sum(grid[mask] * density[mask])
            / np.sum(density[mask])
        )
        expected_shortfall = (
            expected_value_tail / reference_value - 1.0
        )
        probability_of_loss = self._beta_cdf_from_grid(
            min(reference_value, 1.0),
            grid,
            cumulative,
        )
        target_return = (
            None
            if target_value is None
            else target_value / reference_value - 1.0
        )
        probability_of_target_shortfall = (
            None
            if target_value is None
            else self._beta_cdf_from_grid(
                target_value,
                grid,
                cumulative,
            )
        )
        return TailRiskMetrics(
            confidence_level=0.95,
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
    def _normal_explanation(
        *,
        status: BayesianUpdateStatus,
        prior_mean: float,
        posterior_mean: float,
        posterior_std: float,
    ) -> tuple[str, ...]:
        return (
            f"Bayesian update status: {status.value}.",
            (
                f"Posterior mean moved from {prior_mean:.6f} "
                f"to {posterior_mean:.6f}."
            ),
            f"Posterior standard deviation is {posterior_std:.6f}.",
        )

    @staticmethod
    def _beta_explanation(
        *,
        status: BayesianUpdateStatus,
        prior_mean: float,
        posterior_mean: float,
    ) -> tuple[str, ...]:
        return (
            f"Bayesian update status: {status.value}.",
            (
                f"Posterior probability moved from {prior_mean:.6f} "
                f"to {posterior_mean:.6f}."
            ),
        )
