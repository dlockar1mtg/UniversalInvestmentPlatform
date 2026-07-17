"""Shared risk analytics for probabilistic forecast distributions."""

from __future__ import annotations

from collections.abc import Iterable
from math import sqrt

import numpy as np

from .distribution_models import ForecastDistributionResult
from .risk_analytics_contracts import (
    DistributionComparisonEntry,
    DistributionComparisonResult,
    DistributionRiskGrade,
    DistributionRiskMetrics,
    DistributionRiskProfile,
    TailRiskPoint,
)


class DistributionRiskAnalyticsEngine:
    """Analyze and compare canonical forecast distributions."""

    def analyze(
        self,
        distribution: ForecastDistributionResult,
        *,
        profile: DistributionRiskProfile | None = None,
        samples: Iterable[float] | None = None,
        probabilities: Iterable[float] | None = None,
    ) -> DistributionRiskMetrics:
        config = profile or DistributionRiskProfile()
        values, weights = self._resolve_support(
            distribution,
            samples=samples,
            probabilities=probabilities,
        )

        reference = distribution.reference_value
        returns = values / reference - 1.0
        expected_return = float(np.sum(returns * weights))
        median_return = (
            distribution.statistics.median / reference - 1.0
        )
        volatility = float(
            sqrt(
                np.sum(
                    weights * (returns - expected_return) ** 2
                )
            )
        )

        downside_mask = returns < config.downside_target_return
        upside_mask = returns >= config.upside_target_return
        loss_mask = returns < 0.0

        downside_probability = float(weights[downside_mask].sum())
        upside_probability = float(weights[upside_mask].sum())
        probability_of_loss = float(weights[loss_mask].sum())

        downside_gaps = np.minimum(
            returns - config.downside_target_return,
            0.0,
        )
        downside_deviation = float(
            sqrt(np.sum(weights * downside_gaps**2))
        )
        upside_excess = np.maximum(
            returns - config.upside_target_return,
            0.0,
        )
        upside_potential = float(
            np.sum(weights * upside_excess)
        )

        interval = self._interval(
            distribution,
            config.uncertainty_interval_coverage,
        )
        interval_width = interval.upper_value - interval.lower_value
        normalized_interval_width = interval_width / reference

        q25 = self._quantile(distribution, values, weights, 0.25)
        q50 = self._quantile(distribution, values, weights, 0.50)
        q75 = self._quantile(distribution, values, weights, 0.75)
        lower_spread = max(q50 - q25, 0.0)
        upper_spread = max(q75 - q50, 0.0)
        spread_total = lower_spread + upper_spread
        asymmetry_score = (
            0.0
            if spread_total <= 1e-15
            else (upper_spread - lower_spread) / spread_total
        )

        tail_points = tuple(
            self._tail_point(
                returns,
                weights,
                confidence_level,
            )
            for confidence_level in config.var_confidence_levels
        )
        worst = max(
            tail_points,
            key=lambda item: item.confidence_level,
        )
        tail_concentration = min(
            1.0,
            abs(worst.expected_shortfall - worst.value_at_risk)
            / max(volatility, 1e-12),
        )

        target_attainment_probability = (
            distribution.probability_above_target
        )
        risk_adjusted_return = (
            expected_return - config.risk_free_rate
        ) / max(
            downside_deviation,
            volatility,
            1e-12,
        )

        risk_score = self._risk_score(
            probability_of_loss=probability_of_loss,
            normalized_interval_width=normalized_interval_width,
            tail_concentration=tail_concentration,
            downside_deviation=downside_deviation,
        )
        risk_grade = self._risk_grade(risk_score)

        return DistributionRiskMetrics(
            asset_id=distribution.asset_id,
            distribution_id=distribution.distribution_id,
            expected_return=expected_return,
            median_return=median_return,
            volatility=volatility,
            downside_probability=downside_probability,
            upside_probability=upside_probability,
            probability_of_loss=probability_of_loss,
            target_attainment_probability=(
                target_attainment_probability
            ),
            downside_deviation=downside_deviation,
            upside_potential=upside_potential,
            interval_width=interval_width,
            normalized_interval_width=(
                normalized_interval_width
            ),
            asymmetry_score=asymmetry_score,
            tail_concentration=tail_concentration,
            risk_adjusted_return=risk_adjusted_return,
            tail_risk=tail_points,
            risk_score=risk_score,
            risk_grade=risk_grade,
            explanation=(
                (
                    f"Expected return is {expected_return:.2%} with "
                    f"loss probability of {probability_of_loss:.2%}."
                ),
                (
                    f"Normalized uncertainty width is "
                    f"{normalized_interval_width:.2%}."
                ),
                (
                    f"Risk score is {risk_score:.3f}, classified "
                    f"as {risk_grade.value}."
                ),
            ),
            metadata={
                **dict(config.metadata),
                "distribution_family": distribution.family.value,
                "interval_coverage": (
                    config.uncertainty_interval_coverage
                ),
            },
        )

    def compare(
        self,
        metrics: Iterable[DistributionRiskMetrics],
    ) -> DistributionComparisonResult:
        items = tuple(metrics)
        if not items:
            raise ValueError(
                "At least one distribution risk metric is required."
            )

        ordered = sorted(
            items,
            key=lambda item: (
                item.risk_score,
                -item.risk_adjusted_return,
                -item.expected_return,
                item.asset_id,
                item.distribution_id,
            ),
        )
        entries = tuple(
            DistributionComparisonEntry(
                rank=index,
                asset_id=item.asset_id,
                distribution_id=item.distribution_id,
                risk_score=item.risk_score,
                risk_grade=item.risk_grade,
                risk_adjusted_return=item.risk_adjusted_return,
                expected_return=item.expected_return,
                probability_of_loss=item.probability_of_loss,
            )
            for index, item in enumerate(ordered, start=1)
        )
        leader = entries[0]
        return DistributionComparisonResult(
            entries=entries,
            explanation=(
                (
                    f"Lowest-risk distribution is {leader.asset_id} "
                    f"with risk score {leader.risk_score:.3f}."
                ),
            ),
        )

    @staticmethod
    def _resolve_support(
        distribution: ForecastDistributionResult,
        *,
        samples: Iterable[float] | None,
        probabilities: Iterable[float] | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        if samples is not None:
            values = np.array(tuple(samples), dtype=float)
            if values.size == 0:
                raise ValueError("samples cannot be empty.")
            if probabilities is None:
                weights = np.full(
                    values.size,
                    1.0 / values.size,
                    dtype=float,
                )
            else:
                weights = np.array(
                    tuple(probabilities),
                    dtype=float,
                )
                if weights.size != values.size:
                    raise ValueError(
                        "probabilities must match sample count."
                    )
                if np.any(weights < 0):
                    raise ValueError(
                        "probabilities cannot be negative."
                    )
                total = float(weights.sum())
                if total <= 0:
                    raise ValueError(
                        "probabilities must have positive mass."
                    )
                weights = weights / total
            return values, weights

        percentiles = sorted(
            distribution.percentiles,
            key=lambda item: item.probability,
        )
        if not percentiles:
            raise ValueError(
                "Distribution requires percentiles or explicit samples."
            )

        values = np.array(
            [item.value for item in percentiles],
            dtype=float,
        )
        probability_levels = np.array(
            [item.probability for item in percentiles],
            dtype=float,
        )

        boundaries = np.concatenate(
            (
                [0.0],
                (probability_levels[:-1] + probability_levels[1:])
                / 2.0,
                [1.0],
            )
        )
        weights = np.diff(boundaries)
        weights = weights / weights.sum()
        return values, weights

    @staticmethod
    def _interval(
        distribution: ForecastDistributionResult,
        coverage: float,
    ):
        try:
            return distribution.central_interval(coverage)
        except KeyError as exc:
            raise ValueError(
                f"Distribution does not contain a {coverage:.0%} "
                "confidence interval."
            ) from exc

    @staticmethod
    def _quantile(
        distribution: ForecastDistributionResult,
        values: np.ndarray,
        weights: np.ndarray,
        probability: float,
    ) -> float:
        try:
            return distribution.percentile(probability).value
        except KeyError:
            order = np.argsort(values)
            ordered_values = values[order]
            ordered_weights = weights[order]
            cumulative = np.cumsum(ordered_weights)
            index = int(
                np.searchsorted(
                    cumulative,
                    probability,
                    side="left",
                )
            )
            index = min(index, len(ordered_values) - 1)
            return float(ordered_values[index])

    @staticmethod
    def _tail_point(
        returns: np.ndarray,
        weights: np.ndarray,
        confidence_level: float,
    ) -> TailRiskPoint:
        alpha = 1.0 - confidence_level
        order = np.argsort(returns)
        ordered_returns = returns[order]
        ordered_weights = weights[order]
        cumulative = np.cumsum(ordered_weights)
        index = int(
            np.searchsorted(cumulative, alpha, side="left")
        )
        index = min(index, len(ordered_returns) - 1)
        value_at_risk = float(ordered_returns[index])

        tail_mask = ordered_returns <= value_at_risk + 1e-12
        tail_returns = ordered_returns[tail_mask]
        tail_weights = ordered_weights[tail_mask]
        expected_shortfall = float(
            np.sum(tail_returns * tail_weights)
            / tail_weights.sum()
        )
        return TailRiskPoint(
            confidence_level=confidence_level,
            value_at_risk=value_at_risk,
            expected_shortfall=expected_shortfall,
        )

    @staticmethod
    def _risk_score(
        *,
        probability_of_loss: float,
        normalized_interval_width: float,
        tail_concentration: float,
        downside_deviation: float,
    ) -> float:
        width_component = min(
            1.0,
            normalized_interval_width / 2.0,
        )
        downside_component = min(
            1.0,
            downside_deviation,
        )
        score = (
            0.35 * probability_of_loss
            + 0.30 * width_component
            + 0.20 * tail_concentration
            + 0.15 * downside_component
        )
        return min(1.0, max(0.0, score))

    @staticmethod
    def _risk_grade(
        score: float,
    ) -> DistributionRiskGrade:
        if score < 0.20:
            return DistributionRiskGrade.VERY_LOW
        if score < 0.40:
            return DistributionRiskGrade.LOW
        if score < 0.60:
            return DistributionRiskGrade.MODERATE
        if score < 0.80:
            return DistributionRiskGrade.HIGH
        return DistributionRiskGrade.VERY_HIGH
