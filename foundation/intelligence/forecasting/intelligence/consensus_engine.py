"""Forecast consensus, dispersion, and outlier analysis."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from math import sqrt
from statistics import median

from ..models import ForecastDirection
from .consensus_contracts import (
    ConsensusOutlier,
    ConsensusProfile,
    ConsensusStrength,
    ForecastConsensusInput,
    ForecastConsensusResult,
)


class ForecastConsensusEngine:
    """Measure agreement across comparable model forecasts."""

    def __init__(self, profile: ConsensusProfile | None = None) -> None:
        self.profile = profile or ConsensusProfile()

    def analyze(
        self,
        forecasts: Iterable[ForecastConsensusInput],
    ) -> ForecastConsensusResult:
        items = tuple(forecasts)
        if not items:
            raise ValueError("At least one forecast is required.")

        self._validate_comparability(items)

        asset_id = items[0].asset_id
        asset_class = items[0].asset_class
        horizon = items[0].horizon

        if len(items) < self.profile.minimum_model_count:
            return ForecastConsensusResult(
                asset_id=asset_id,
                asset_class=asset_class,
                horizon=horizon,
                model_count=len(items),
                consensus_value=items[0].point_forecast,
                consensus_direction=items[0].direction,
                value_agreement_score=0.0,
                direction_agreement_score=0.0,
                quality_agreement_score=0.0,
                consensus_score=0.0,
                strength=ConsensusStrength.INSUFFICIENT,
                dispersion_ratio=None,
                confidence_adjustment=-self.profile.maximum_confidence_penalty,
                explanation=(
                    "Insufficient independent model forecasts for consensus.",
                ),
            )

        values = [item.point_forecast for item in items]
        qualities = [item.model_quality for item in items]
        weights = self._normalized_quality_weights(qualities)
        consensus_value = sum(
            value * weight for value, weight in zip(values, weights)
        )

        standard_deviation = self._population_std(values)
        mean_value = sum(values) / len(values)
        dispersion_ratio = (
            standard_deviation / abs(mean_value)
            if mean_value != 0
            else standard_deviation
        )
        value_agreement = 1.0 / (1.0 + dispersion_ratio)

        consensus_direction, direction_agreement = self._direction_consensus(
            items
        )
        quality_agreement = self._quality_agreement(qualities)

        consensus_score = (
            value_agreement * self.profile.value_agreement_weight
            + direction_agreement
            * self.profile.direction_agreement_weight
            + quality_agreement
            * self.profile.quality_agreement_weight
        )
        outliers = self._detect_outliers(items, consensus_value)

        if outliers:
            consensus_score *= max(
                0.0,
                1.0 - len(outliers) / len(items),
            )

        consensus_score = min(1.0, max(0.0, consensus_score))
        strength = self._strength(consensus_score)
        confidence_adjustment = self._confidence_adjustment(
            consensus_score,
            strength,
        )
        explanation = self._build_explanation(
            items=items,
            strength=strength,
            consensus_score=consensus_score,
            direction=consensus_direction,
            direction_agreement=direction_agreement,
            dispersion_ratio=dispersion_ratio,
            outliers=outliers,
        )

        return ForecastConsensusResult(
            asset_id=asset_id,
            asset_class=asset_class,
            horizon=horizon,
            model_count=len(items),
            consensus_value=consensus_value,
            consensus_direction=consensus_direction,
            value_agreement_score=value_agreement,
            direction_agreement_score=direction_agreement,
            quality_agreement_score=quality_agreement,
            consensus_score=consensus_score,
            strength=strength,
            dispersion_ratio=dispersion_ratio,
            confidence_adjustment=confidence_adjustment,
            outliers=outliers,
            explanation=explanation,
            metrics={
                "mean_forecast": mean_value,
                "standard_deviation": standard_deviation,
                "minimum_forecast": min(values),
                "maximum_forecast": max(values),
            },
        )

    @staticmethod
    def _validate_comparability(
        items: tuple[ForecastConsensusInput, ...],
    ) -> None:
        first = items[0]
        for item in items[1:]:
            if item.asset_id != first.asset_id:
                raise ValueError(
                    "Consensus inputs must share the same asset_id."
                )
            if item.asset_class != first.asset_class:
                raise ValueError(
                    "Consensus inputs must share the same asset_class."
                )
            if item.horizon is not first.horizon:
                raise ValueError(
                    "Consensus inputs must share the same horizon."
                )
            if item.reference_value != first.reference_value:
                raise ValueError(
                    "Consensus inputs must share the same reference_value."
                )

        keys = [item.model_key for item in items]
        if len(keys) != len(set(keys)):
            raise ValueError(
                "Consensus inputs cannot contain duplicate model versions."
            )

    @staticmethod
    def _normalized_quality_weights(
        qualities: list[float],
    ) -> list[float]:
        total = sum(qualities)
        if total == 0:
            return [1.0 / len(qualities)] * len(qualities)
        return [quality / total for quality in qualities]

    @staticmethod
    def _population_std(values: list[float]) -> float:
        mean_value = sum(values) / len(values)
        variance = sum(
            (value - mean_value) ** 2 for value in values
        ) / len(values)
        return sqrt(variance)

    @staticmethod
    def _quality_agreement(qualities: list[float]) -> float:
        if len(qualities) <= 1:
            return 0.0
        spread = max(qualities) - min(qualities)
        return max(0.0, 1.0 - spread)

    @staticmethod
    def _direction_consensus(
        items: tuple[ForecastConsensusInput, ...],
    ) -> tuple[ForecastDirection, float]:
        known = [
            item.direction
            for item in items
            if item.direction is not ForecastDirection.UNKNOWN
        ]
        if not known:
            return ForecastDirection.UNKNOWN, 0.0

        counts = Counter(known)
        direction, count = sorted(
            counts.items(),
            key=lambda pair: (-pair[1], pair[0].value),
        )[0]
        return direction, count / len(items)

    def _detect_outliers(
        self,
        items: tuple[ForecastConsensusInput, ...],
        consensus_value: float,
    ) -> tuple[ConsensusOutlier, ...]:
        values = [item.point_forecast for item in items]
        center = median(values)
        absolute_deviations = [
            abs(value - center) for value in values
        ]
        mad = median(absolute_deviations)

        if mad == 0:
            non_center = [
                abs(value - center)
                for value in values
                if value != center
            ]
            if not non_center:
                return ()
            scale = min(non_center)
        else:
            scale = 1.4826 * mad

        outliers: list[ConsensusOutlier] = []
        for item in items:
            robust_z = abs(item.point_forecast - center) / scale
            if robust_z >= self.profile.outlier_z_threshold:
                deviation = (
                    (item.point_forecast / consensus_value) - 1.0
                    if consensus_value != 0
                    else item.point_forecast - consensus_value
                )
                outliers.append(
                    ConsensusOutlier(
                        engine_name=item.engine_name,
                        engine_version=item.engine_version,
                        point_forecast=item.point_forecast,
                        robust_z_score=robust_z,
                        deviation_from_consensus=deviation,
                    )
                )

        return tuple(
            sorted(
                outliers,
                key=lambda item: (
                    -item.robust_z_score,
                    item.engine_name,
                    item.engine_version,
                ),
            )
        )

    @staticmethod
    def _strength(score: float) -> ConsensusStrength:
        if score >= 0.90:
            return ConsensusStrength.VERY_STRONG
        if score >= 0.78:
            return ConsensusStrength.STRONG
        if score >= 0.62:
            return ConsensusStrength.MODERATE
        if score >= 0.45:
            return ConsensusStrength.WEAK
        return ConsensusStrength.CONFLICTED

    def _confidence_adjustment(
        self,
        score: float,
        strength: ConsensusStrength,
    ) -> float:
        if strength in (
            ConsensusStrength.VERY_STRONG,
            ConsensusStrength.STRONG,
        ):
            return (
                self.profile.maximum_confidence_boost
                * max(0.0, (score - 0.78) / (1.0 - 0.78))
            )
        if strength in (
            ConsensusStrength.WEAK,
            ConsensusStrength.CONFLICTED,
        ):
            return -(
                self.profile.maximum_confidence_penalty
                * max(0.0, (0.62 - score) / 0.62)
            )
        return 0.0

    @staticmethod
    def _build_explanation(
        *,
        items: tuple[ForecastConsensusInput, ...],
        strength: ConsensusStrength,
        consensus_score: float,
        direction: ForecastDirection,
        direction_agreement: float,
        dispersion_ratio: float,
        outliers: tuple[ConsensusOutlier, ...],
    ) -> tuple[str, ...]:
        messages = [
            (
                f"{len(items)} models produced "
                f"{strength.value.replace('_', ' ')} consensus "
                f"({consensus_score:.3f})."
            ),
            (
                f"Directional agreement was "
                f"{direction_agreement:.1%} toward {direction.value}."
            ),
            f"Forecast dispersion ratio was {dispersion_ratio:.4f}.",
        ]
        if outliers:
            names = ", ".join(
                f"{item.engine_name} {item.engine_version}"
                for item in outliers
            )
            messages.append(f"Outlier forecasts detected: {names}.")
        else:
            messages.append("No material forecast outliers were detected.")
        return tuple(messages)
