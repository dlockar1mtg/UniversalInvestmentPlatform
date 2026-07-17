"""Dynamic ensemble model weight optimization engine."""

from __future__ import annotations

from collections.abc import Iterable

from .weighting_contracts import (
    EnsembleModelSignal,
    EnsembleWeightEntry,
    EnsembleWeightProfile,
    EnsembleWeightResult,
    WeightOptimizationStatus,
)


class EnsembleWeightOptimizationEngine:
    """Assign normalized and constrained weights to forecast models."""

    def __init__(
        self,
        profile: EnsembleWeightProfile | None = None,
    ) -> None:
        self.profile = profile or EnsembleWeightProfile()

    def optimize(
        self,
        signals: Iterable[EnsembleModelSignal],
    ) -> EnsembleWeightResult:
        items = tuple(signals)
        if not items:
            raise ValueError("At least one ensemble model signal is required.")

        self._validate_comparability(items)

        eligible = tuple(
            item
            for item in items
            if item.eligible or not self.profile.exclude_ineligible_models
        )
        excluded_count = len(items) - len(eligible)

        if len(eligible) < self.profile.minimum_model_count:
            return EnsembleWeightResult(
                asset_class=items[0].asset_class,
                horizon=items[0].horizon,
                regime=items[0].regime,
                status=WeightOptimizationStatus.INSUFFICIENT,
                weights=(),
                eligible_model_count=len(eligible),
                excluded_model_count=excluded_count,
                explanation=(
                    "Insufficient eligible models for ensemble optimization.",
                ),
            )

        raw_scores = {
            item.model_key: self._raw_score(item)
            for item in eligible
        }
        raw_total = sum(raw_scores.values())

        if raw_total == 0:
            equal_weight = 1.0 / len(eligible)
            entries = tuple(
                EnsembleWeightEntry(
                    engine_name=item.engine_name,
                    engine_version=item.engine_version,
                    raw_score=0.0,
                    normalized_weight=equal_weight,
                    constrained_weight=equal_weight,
                    eligible=item.eligible,
                    factors=self._factors(item),
                    explanation=(
                        "Equal fallback weight used because all raw scores "
                        "were zero.",
                    ),
                )
                for item in sorted(
                    eligible,
                    key=lambda value: value.model_key,
                )
            )
            return EnsembleWeightResult(
                asset_class=items[0].asset_class,
                horizon=items[0].horizon,
                regime=items[0].regime,
                status=WeightOptimizationStatus.FALLBACK_EQUAL,
                weights=entries,
                eligible_model_count=len(eligible),
                excluded_model_count=excluded_count,
                explanation=(
                    "All optimization signals were zero; equal weights applied.",
                ),
                metrics={"raw_score_total": 0.0},
            )

        normalized = {
            key: score / raw_total
            for key, score in raw_scores.items()
        }
        constrained = self._apply_constraints(normalized)

        entries = tuple(
            EnsembleWeightEntry(
                engine_name=item.engine_name,
                engine_version=item.engine_version,
                raw_score=raw_scores[item.model_key],
                normalized_weight=normalized[item.model_key],
                constrained_weight=constrained[item.model_key],
                eligible=item.eligible,
                factors=self._factors(item),
                explanation=self._entry_explanation(
                    item,
                    constrained[item.model_key],
                ),
            )
            for item in sorted(
                eligible,
                key=lambda value: (
                    -constrained[value.model_key],
                    value.engine_name,
                    value.engine_version,
                ),
            )
        )

        return EnsembleWeightResult(
            asset_class=items[0].asset_class,
            horizon=items[0].horizon,
            regime=items[0].regime,
            status=WeightOptimizationStatus.OPTIMIZED,
            weights=entries,
            eligible_model_count=len(eligible),
            excluded_model_count=excluded_count,
            explanation=self._result_explanation(entries, excluded_count),
            metrics={
                "raw_score_total": raw_total,
                "largest_weight": max(
                    entry.constrained_weight for entry in entries
                ),
                "smallest_weight": min(
                    entry.constrained_weight for entry in entries
                ),
            },
        )

    def _raw_score(self, signal: EnsembleModelSignal) -> float:
        return (
            signal.model_quality_score * self.profile.quality_weight
            + signal.calibrated_confidence
            * self.profile.calibrated_confidence_weight
            + signal.consensus_alignment_score
            * self.profile.consensus_alignment_weight
            + signal.reliability_score
            * self.profile.reliability_weight
            + signal.regime_match_score
            * self.profile.regime_match_weight
        )

    @staticmethod
    def _factors(signal: EnsembleModelSignal) -> dict[str, float]:
        return {
            "model_quality_score": signal.model_quality_score,
            "calibrated_confidence": signal.calibrated_confidence,
            "consensus_alignment_score": (
                signal.consensus_alignment_score
            ),
            "reliability_score": signal.reliability_score,
            "regime_match_score": signal.regime_match_score,
        }

    def _apply_constraints(
        self,
        normalized: dict[tuple[str, str], float],
    ) -> dict[tuple[str, str], float]:
        constrained = dict(normalized)
        keys = tuple(constrained)

        for _ in range(100):
            changed = False
            for key in keys:
                value = constrained[key]
                bounded = min(
                    self.profile.maximum_model_weight,
                    max(self.profile.minimum_model_weight, value),
                )
                if abs(bounded - value) > 1e-12:
                    constrained[key] = bounded
                    changed = True

            total = sum(constrained.values())
            difference = 1.0 - total
            if abs(difference) <= 1e-12:
                break

            if difference > 0:
                adjustable = [
                    key for key in keys
                    if constrained[key]
                    < self.profile.maximum_model_weight - 1e-12
                ]
                if not adjustable:
                    break
                capacity = sum(
                    self.profile.maximum_model_weight - constrained[key]
                    for key in adjustable
                )
                if capacity <= 0:
                    break
                for key in adjustable:
                    share = (
                        self.profile.maximum_model_weight
                        - constrained[key]
                    ) / capacity
                    constrained[key] += difference * share
            else:
                adjustable = [
                    key for key in keys
                    if constrained[key]
                    > self.profile.minimum_model_weight + 1e-12
                ]
                if not adjustable:
                    break
                capacity = sum(
                    constrained[key] - self.profile.minimum_model_weight
                    for key in adjustable
                )
                if capacity <= 0:
                    break
                for key in adjustable:
                    share = (
                        constrained[key] - self.profile.minimum_model_weight
                    ) / capacity
                    constrained[key] += difference * share

            if not changed and abs(sum(constrained.values()) - 1.0) <= 1e-12:
                break

        total = sum(constrained.values())
        if total <= 0:
            equal = 1.0 / len(constrained)
            return {key: equal for key in constrained}

        constrained = {
            key: value / total
            for key, value in constrained.items()
        }

        if any(
            value > self.profile.maximum_model_weight + 1e-9
            or value < self.profile.minimum_model_weight - 1e-9
            for value in constrained.values()
        ):
            raise ValueError(
                "Ensemble weight constraints are infeasible for "
                "the number of eligible models."
            )

        return constrained

    @staticmethod
    def _validate_comparability(
        items: tuple[EnsembleModelSignal, ...],
    ) -> None:
        first = items[0]
        keys = [item.model_key for item in items]

        if len(keys) != len(set(keys)):
            raise ValueError(
                "Ensemble signals cannot contain duplicate model versions."
            )

        for item in items[1:]:
            if item.asset_class != first.asset_class:
                raise ValueError(
                    "Ensemble signals must share the same asset_class."
                )
            if item.horizon is not first.horizon:
                raise ValueError(
                    "Ensemble signals must share the same horizon."
                )
            if item.regime is not first.regime:
                raise ValueError(
                    "Ensemble signals must share the same regime."
                )

    @staticmethod
    def _entry_explanation(
        signal: EnsembleModelSignal,
        weight: float,
    ) -> tuple[str, ...]:
        strongest_factor = max(
            {
                "quality": signal.model_quality_score,
                "calibrated confidence": signal.calibrated_confidence,
                "consensus alignment": signal.consensus_alignment_score,
                "reliability": signal.reliability_score,
                "regime match": signal.regime_match_score,
            }.items(),
            key=lambda item: (item[1], item[0]),
        )
        return (
            f"Final constrained ensemble weight was {weight:.4f}.",
            (
                f"Strongest contributing factor was "
                f"{strongest_factor[0]} ({strongest_factor[1]:.3f})."
            ),
        )

    @staticmethod
    def _result_explanation(
        entries: tuple[EnsembleWeightEntry, ...],
        excluded_count: int,
    ) -> tuple[str, ...]:
        leader = entries[0]
        return (
            (
                f"Optimized weights across {len(entries)} eligible models."
            ),
            (
                f"Highest weight assigned to {leader.engine_name} "
                f"{leader.engine_version} "
                f"({leader.constrained_weight:.3f})."
            ),
            f"Excluded {excluded_count} ineligible models.",
        )
