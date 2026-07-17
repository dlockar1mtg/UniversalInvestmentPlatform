"""Forecast drift-detection engine."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timezone

from .drift_contracts import (
    DriftDetectionProfile,
    DriftHistory,
    DriftHistoryEntry,
    DriftMetric,
    DriftRecommendation,
    DriftSeverity,
    DriftType,
    ForecastDriftReport,
    ForecastDriftSignal,
    RegimePerformanceSnapshot,
)
from .performance_contracts import (
    ForecastPerformanceMetrics,
    PerformanceGrouping,
)


class ForecastDriftDetectionEngine:
    """Compare baseline and current scorecards for model drift."""

    def detect(
        self,
        baseline_scorecards: Iterable[ForecastPerformanceMetrics],
        current_scorecards: Iterable[ForecastPerformanceMetrics],
        *,
        baseline_regime: str = "unknown",
        current_regime: str = "unknown",
        prior_history: DriftHistory | None = None,
        profile: DriftDetectionProfile | None = None,
        as_of_date: date | None = None,
    ) -> ForecastDriftReport:
        config = profile or DriftDetectionProfile()
        baseline = self._index_scorecards(baseline_scorecards)
        current = self._index_scorecards(current_scorecards)

        if not baseline or not current:
            raise ValueError(
                "Baseline and current scorecards are required."
            )
        if set(baseline) != set(current):
            raise ValueError(
                "Baseline and current model keys must match."
            )
        if not baseline_regime.strip() or not current_regime.strip():
            raise ValueError("Regime names are required.")

        effective_date = as_of_date or max(
            item.evaluation_end for item in current.values()
        )
        regime_changed = baseline_regime != current_regime

        signals = tuple(
            self._signal(
                baseline=baseline[model_key],
                current=current[model_key],
                baseline_regime=baseline_regime,
                current_regime=current_regime,
                regime_changed=regime_changed,
                profile=config,
                as_of_date=effective_date,
            )
            for model_key in sorted(current)
        )

        memory = tuple(
            RegimePerformanceSnapshot(
                model_key=item.group_key,
                regime=current_regime,
                as_of_date=effective_date,
                sample_size=item.sample_size,
                performance_score=item.score,
                mae=item.mae,
                directional_accuracy=item.directional_accuracy,
                interval_coverage=item.interval_coverage,
                metadata={
                    "grade": item.grade.value,
                    "eligible": item.eligible,
                },
            )
            for item in sorted(
                current.values(),
                key=lambda value: value.group_key,
            )
        )

        existing = (
            prior_history.entries
            if prior_history is not None
            else ()
        )
        new_entries = tuple(
            DriftHistoryEntry(
                model_key=signal.model_key,
                evaluated_at=datetime.now(timezone.utc),
                drift_score=signal.drift_score,
                severity=signal.severity,
                recommendation=signal.recommendation,
                baseline_regime=signal.baseline_regime,
                current_regime=signal.current_regime,
                metrics={
                    metric.drift_type.value: metric.normalized_score
                    for metric in signal.metrics
                },
            )
            for signal in signals
        )

        return ForecastDriftReport(
            signals=signals,
            regime_memory=memory,
            history=DriftHistory(entries=existing + new_entries),
        )

    @staticmethod
    def _index_scorecards(
        scorecards: Iterable[ForecastPerformanceMetrics],
    ) -> dict[str, ForecastPerformanceMetrics]:
        items = tuple(scorecards)
        if any(
            item.grouping is not PerformanceGrouping.MODEL
            for item in items
        ):
            raise ValueError(
                "Drift detection requires model-grouped scorecards."
            )
        keys = [item.group_key for item in items]
        if len(keys) != len(set(keys)):
            raise ValueError("Model scorecard keys must be unique.")
        return {item.group_key: item for item in items}

    def _signal(
        self,
        *,
        baseline: ForecastPerformanceMetrics,
        current: ForecastPerformanceMetrics,
        baseline_regime: str,
        current_regime: str,
        regime_changed: bool,
        profile: DriftDetectionProfile,
        as_of_date: date,
    ) -> ForecastDriftSignal:
        performance_change = baseline.score - current.score
        error_change = self._relative_error_change(
            baseline.mae,
            current.mae,
            profile.maximum_relative_error_change,
        )
        bias_change = abs(current.mean_bias) - abs(baseline.mean_bias)
        direction_change = self._optional_decline(
            baseline.directional_accuracy,
            current.directional_accuracy,
        )
        calibration_change = self._optional_decline(
            self._coverage_quality(baseline),
            self._coverage_quality(current),
        )

        metrics = (
            DriftMetric(
                drift_type=DriftType.PERFORMANCE,
                raw_change=performance_change,
                normalized_score=self._positive_unit(
                    performance_change
                ),
                explanation=(
                    f"Performance score changed from "
                    f"{baseline.score:.3f} to {current.score:.3f}."
                ),
            ),
            DriftMetric(
                drift_type=DriftType.ERROR,
                raw_change=error_change,
                normalized_score=self._positive_unit(error_change),
                explanation=(
                    f"MAE changed from {baseline.mae:.6f} "
                    f"to {current.mae:.6f}."
                ),
            ),
            DriftMetric(
                drift_type=DriftType.BIAS,
                raw_change=bias_change,
                normalized_score=self._normalize_bias(
                    bias_change,
                    baseline,
                ),
                explanation=(
                    f"Absolute bias changed from "
                    f"{abs(baseline.mean_bias):.6f} to "
                    f"{abs(current.mean_bias):.6f}."
                ),
            ),
            DriftMetric(
                drift_type=DriftType.DIRECTION,
                raw_change=direction_change,
                normalized_score=self._positive_unit(
                    direction_change
                ),
                explanation=(
                    "Directional accuracy deterioration was "
                    f"{direction_change:.3f}."
                ),
            ),
            DriftMetric(
                drift_type=DriftType.CALIBRATION,
                raw_change=calibration_change,
                normalized_score=self._positive_unit(
                    calibration_change
                ),
                explanation=(
                    "Interval-calibration deterioration was "
                    f"{calibration_change:.3f}."
                ),
            ),
        )

        score = (
            profile.performance_weight
            * metrics[0].normalized_score
            + profile.error_weight
            * metrics[1].normalized_score
            + profile.bias_weight
            * metrics[2].normalized_score
            + profile.direction_weight
            * metrics[3].normalized_score
            + profile.calibration_weight
            * metrics[4].normalized_score
        )
        if regime_changed:
            score += profile.regime_penalty
        if (
            baseline.sample_size < profile.minimum_sample_size
            or current.sample_size < profile.minimum_sample_size
        ):
            score = max(score, profile.moderate_threshold)

        score = min(1.0, max(0.0, score))
        severity = self._severity(score, profile)
        recommendation = self._recommendation(
            severity=severity,
            regime_changed=regime_changed,
            current=current,
        )

        return ForecastDriftSignal(
            model_key=current.group_key,
            as_of_date=as_of_date,
            baseline_sample_size=baseline.sample_size,
            current_sample_size=current.sample_size,
            baseline_regime=baseline_regime,
            current_regime=current_regime,
            metrics=metrics,
            drift_score=score,
            severity=severity,
            recommendation=recommendation,
            regime_changed=regime_changed,
            explanation=(
                (
                    f"Composite drift score is {score:.3f}, "
                    f"classified {severity.value}."
                ),
                (
                    f"Recommended action is "
                    f"{recommendation.value}."
                ),
            ),
            metadata={
                **dict(profile.metadata),
                "baseline_grade": baseline.grade.value,
                "current_grade": current.grade.value,
            },
        )

    @staticmethod
    def _relative_error_change(
        baseline: float,
        current: float,
        maximum_change: float,
    ) -> float:
        if baseline <= 1e-12:
            return 0.0 if current <= 1e-12 else 1.0
        change = (current - baseline) / baseline
        return min(
            1.0,
            max(-1.0, change / maximum_change),
        )

    @staticmethod
    def _optional_decline(
        baseline: float | None,
        current: float | None,
    ) -> float:
        if baseline is None or current is None:
            return 0.0
        return baseline - current

    @staticmethod
    def _coverage_quality(
        metrics: ForecastPerformanceMetrics,
    ) -> float | None:
        if metrics.interval_coverage_gap is None:
            return None
        return max(
            0.0,
            1.0 - abs(metrics.interval_coverage_gap),
        )

    @staticmethod
    def _positive_unit(value: float) -> float:
        return min(1.0, max(0.0, value))

    @staticmethod
    def _normalize_bias(
        change: float,
        baseline: ForecastPerformanceMetrics,
    ) -> float:
        reference = max(abs(baseline.mean_bias), baseline.mae, 1e-12)
        return min(1.0, max(0.0, change / reference))

    @staticmethod
    def _severity(
        score: float,
        profile: DriftDetectionProfile,
    ) -> DriftSeverity:
        if score >= profile.critical_threshold:
            return DriftSeverity.CRITICAL
        if score >= profile.high_threshold:
            return DriftSeverity.HIGH
        if score >= profile.moderate_threshold:
            return DriftSeverity.MODERATE
        if score >= profile.low_threshold:
            return DriftSeverity.LOW
        return DriftSeverity.NONE

    @staticmethod
    def _recommendation(
        *,
        severity: DriftSeverity,
        regime_changed: bool,
        current: ForecastPerformanceMetrics,
    ) -> DriftRecommendation:
        if severity is DriftSeverity.CRITICAL:
            return (
                DriftRecommendation.RETIRE
                if current.score < 0.30
                else DriftRecommendation.RETRAIN
            )
        if severity is DriftSeverity.HIGH:
            return DriftRecommendation.RETRAIN
        if severity is DriftSeverity.MODERATE:
            return (
                DriftRecommendation.RECALIBRATE
                if regime_changed
                else DriftRecommendation.REDUCE_WEIGHT
            )
        if severity is DriftSeverity.LOW:
            return DriftRecommendation.MONITOR
        return DriftRecommendation.NONE
