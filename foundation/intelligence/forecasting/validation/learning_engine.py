"""Continuous-learning engine for model reputation and adaptive weights."""

from __future__ import annotations

from datetime import date, datetime, timezone
from math import exp, log
from collections.abc import Iterable

from .learning_contracts import (
    ContinuousLearningProfile,
    ContinuousLearningResult,
    LearningState,
    ModelLearningSignal,
    ModelLearningSnapshot,
    ModelLearningStatus,
)
from .performance_contracts import (
    ForecastPerformanceMetrics,
    PerformanceGrouping,
)


class ContinuousLearningEngine:
    """Convert model scorecards into reputation and weight updates."""

    def learn(
        self,
        scorecards: Iterable[ForecastPerformanceMetrics],
        *,
        current_weights: dict[str, float] | None = None,
        prior_state: LearningState | None = None,
        profile: ContinuousLearningProfile | None = None,
        as_of_date: date | None = None,
    ) -> ContinuousLearningResult:
        config = profile or ContinuousLearningProfile()
        items = tuple(scorecards)
        if not items:
            raise ValueError(
                "At least one model performance scorecard is required."
            )
        if any(
            item.grouping is not PerformanceGrouping.MODEL
            for item in items
        ):
            raise ValueError(
                "Continuous learning requires model-grouped scorecards."
            )

        model_keys = [item.group_key for item in items]
        if len(model_keys) != len(set(model_keys)):
            raise ValueError("Model scorecard keys must be unique.")

        effective_date = as_of_date or max(
            item.evaluation_end for item in items
        )
        current = current_weights or self._equal_weights(model_keys)
        self._validate_weights(current, model_keys)

        prior_by_key = {
            item.model_key: item
            for item in (prior_state.snapshots if prior_state else ())
        }

        raw_signals = [
            self._signal(
                scorecard=item,
                current_weight=current[item.group_key],
                prior=prior_by_key.get(item.group_key),
                profile=config,
                as_of_date=effective_date,
            )
            for item in items
        ]
        normalized_weights = self._normalize_weights(
            {
                signal.model_key: signal.recommended_weight
                for signal in raw_signals
            },
            minimum=config.minimum_model_weight,
            maximum=config.maximum_model_weight,
        )

        signals = tuple(
            ModelLearningSignal(
                model_key=signal.model_key,
                as_of_date=signal.as_of_date,
                sample_size=signal.sample_size,
                performance_score=signal.performance_score,
                prior_reputation=signal.prior_reputation,
                recency_score=signal.recency_score,
                stability_score=signal.stability_score,
                new_reputation=signal.new_reputation,
                reputation_change=signal.reputation_change,
                status=signal.status,
                current_weight=signal.current_weight,
                recommended_weight=normalized_weights[
                    signal.model_key
                ],
                weight_change=(
                    normalized_weights[signal.model_key]
                    - signal.current_weight
                ),
                explanation=signal.explanation,
                metadata=signal.metadata,
            )
            for signal in raw_signals
        )

        snapshots = tuple(
            ModelLearningSnapshot(
                model_key=signal.model_key,
                reputation=signal.new_reputation,
                adaptive_weight=signal.recommended_weight,
                status=signal.status,
                sample_size=signal.sample_size,
                updated_at=datetime.now(timezone.utc),
                update_count=(
                    1
                    if signal.model_key not in prior_by_key
                    else prior_by_key[signal.model_key].update_count + 1
                ),
                metadata={
                    **dict(signal.metadata),
                    "performance_score": signal.performance_score,
                },
            )
            for signal in sorted(
                signals,
                key=lambda value: value.model_key,
            )
        )

        return ContinuousLearningResult(
            signals=tuple(
                sorted(
                    signals,
                    key=lambda value: (
                        -value.new_reputation,
                        value.model_key,
                    ),
                )
            ),
            state=LearningState(snapshots=snapshots),
        )

    def _signal(
        self,
        *,
        scorecard: ForecastPerformanceMetrics,
        current_weight: float,
        prior: ModelLearningSnapshot | None,
        profile: ContinuousLearningProfile,
        as_of_date: date,
    ) -> ModelLearningSignal:
        prior_reputation = (
            profile.baseline_reputation
            if prior is None
            else prior.reputation
        )
        age_days = max(
            0,
            (as_of_date - scorecard.evaluation_end).days,
        )
        recency_score = exp(
            -log(2.0)
            * age_days
            / profile.recency_half_life_days
        )
        stability_score = self._stability_score(scorecard)

        if not scorecard.eligible:
            new_reputation = min(
                prior_reputation,
                profile.demotion_threshold,
            )
            status = ModelLearningStatus.INELIGIBLE
        else:
            evidence_score = (
                profile.performance_weight * scorecard.score
                + profile.recency_weight * recency_score
                + profile.stability_weight * stability_score
            )
            sample_support = min(
                1.0,
                scorecard.sample_size
                / max(profile.minimum_sample_size, 1),
            )
            learning_rate = 0.25 + 0.50 * sample_support
            new_reputation = (
                prior_reputation
                + learning_rate
                * (evidence_score - prior_reputation)
            )
            new_reputation = min(1.0, max(0.0, new_reputation))
            status = self._status(new_reputation, profile)

        desired_weight = current_weight * (
            0.50 + new_reputation
        )
        lower = max(
            profile.minimum_model_weight,
            current_weight - profile.maximum_weight_change,
        )
        upper = min(
            profile.maximum_model_weight,
            current_weight + profile.maximum_weight_change,
        )
        bounded_weight = min(upper, max(lower, desired_weight))

        return ModelLearningSignal(
            model_key=scorecard.group_key,
            as_of_date=as_of_date,
            sample_size=scorecard.sample_size,
            performance_score=scorecard.score,
            prior_reputation=prior_reputation,
            recency_score=recency_score,
            stability_score=stability_score,
            new_reputation=new_reputation,
            reputation_change=new_reputation - prior_reputation,
            status=status,
            current_weight=current_weight,
            recommended_weight=bounded_weight,
            weight_change=bounded_weight - current_weight,
            explanation=(
                (
                    f"Performance score {scorecard.score:.3f}, "
                    f"recency {recency_score:.3f}, and stability "
                    f"{stability_score:.3f} produced reputation "
                    f"{new_reputation:.3f}."
                ),
                (
                    f"Model status is {status.value}; provisional "
                    f"weight is {bounded_weight:.3f}."
                ),
            ),
            metadata={
                "performance_grade": scorecard.grade.value,
                "evaluation_start": (
                    scorecard.evaluation_start.isoformat()
                ),
                "evaluation_end": (
                    scorecard.evaluation_end.isoformat()
                ),
            },
        )

    @staticmethod
    def _stability_score(
        scorecard: ForecastPerformanceMetrics,
    ) -> float:
        bias_penalty = min(
            1.0,
            abs(scorecard.mean_relative_bias or 0.0),
        )
        coverage_penalty = min(
            1.0,
            abs(scorecard.interval_coverage_gap or 0.0),
        )
        return max(
            0.0,
            1.0 - 0.60 * bias_penalty - 0.40 * coverage_penalty,
        )

    @staticmethod
    def _status(
        reputation: float,
        profile: ContinuousLearningProfile,
    ) -> ModelLearningStatus:
        if reputation >= profile.promotion_threshold:
            return ModelLearningStatus.PROMOTED
        if reputation < profile.demotion_threshold:
            return ModelLearningStatus.DEMOTED
        if reputation < profile.watch_threshold:
            return ModelLearningStatus.WATCH
        return ModelLearningStatus.STABLE

    @staticmethod
    def _equal_weights(model_keys: list[str]) -> dict[str, float]:
        weight = 1.0 / len(model_keys)
        return {key: weight for key in model_keys}

    @staticmethod
    def _validate_weights(
        weights: dict[str, float],
        model_keys: list[str],
    ) -> None:
        if set(weights) != set(model_keys):
            raise ValueError(
                "Current weights must match model scorecard keys."
            )
        if any(value < 0.0 for value in weights.values()):
            raise ValueError("Current weights cannot be negative.")
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise ValueError("Current weights must sum to 1.0.")

    @staticmethod
    def _normalize_weights(
        weights: dict[str, float],
        *,
        minimum: float,
        maximum: float,
    ) -> dict[str, float]:
        total = sum(weights.values())
        if total <= 0:
            equal = 1.0 / len(weights)
            return {key: equal for key in weights}

        normalized = {
            key: value / total
            for key, value in weights.items()
        }

        for _ in range(20):
            clipped = {
                key: min(maximum, max(minimum, value))
                for key, value in normalized.items()
            }
            clipped_total = sum(clipped.values())
            if abs(clipped_total - 1.0) <= 1e-12:
                return clipped
            free = [
                key
                for key, value in clipped.items()
                if minimum < value < maximum
            ]
            if not free:
                return {
                    key: value / clipped_total
                    for key, value in clipped.items()
                }
            adjustment = (1.0 - clipped_total) / len(free)
            normalized = {
                key: (
                    value + adjustment
                    if key in free
                    else value
                )
                for key, value in clipped.items()
            }

        final_total = sum(normalized.values())
        return {
            key: value / final_total
            for key, value in normalized.items()
        }
