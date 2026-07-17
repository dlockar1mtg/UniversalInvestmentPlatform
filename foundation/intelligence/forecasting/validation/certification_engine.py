"""Forecast certification and production-readiness engine."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256

from .certification_contracts import (
    CertificationGate,
    CertificationGateResult,
    CertificationStatus,
    ForecastCertificationProfile,
    ForecastCertificationRecord,
    ForecastCertificationReport,
)
from .drift_contracts import ForecastDriftSignal
from .learning_contracts import ModelLearningSignal
from .performance_contracts import (
    ForecastPerformanceMetrics,
    PerformanceGrouping,
)


class ForecastCertificationEngine:
    """Evaluate model readiness using performance, learning, and drift."""

    def certify(
        self,
        performance: Iterable[ForecastPerformanceMetrics],
        learning: Iterable[ModelLearningSignal],
        drift: Iterable[ForecastDriftSignal],
        *,
        profile: ForecastCertificationProfile | None = None,
        effective_date: date | None = None,
    ) -> ForecastCertificationReport:
        config = profile or ForecastCertificationProfile()
        performance_by_key = self._index_performance(performance)
        learning_by_key = self._index_learning(learning)
        drift_by_key = self._index_drift(drift)

        keys = set(performance_by_key)
        if keys != set(learning_by_key) or keys != set(drift_by_key):
            raise ValueError(
                "Performance, learning, and drift model keys must match."
            )
        if not keys:
            raise ValueError(
                "At least one model is required for certification."
            )

        date_value = effective_date or max(
            item.evaluation_end
            for item in performance_by_key.values()
        )
        records = tuple(
            self._certify_one(
                performance=performance_by_key[key],
                learning=learning_by_key[key],
                drift=drift_by_key[key],
                profile=config,
                effective_date=date_value,
            )
            for key in sorted(keys)
        )
        return ForecastCertificationReport(records=records)

    def _certify_one(
        self,
        *,
        performance: ForecastPerformanceMetrics,
        learning: ModelLearningSignal,
        drift: ForecastDriftSignal,
        profile: ForecastCertificationProfile,
        effective_date: date,
    ) -> ForecastCertificationRecord:
        gates = (
            self._minimum_gate(
                gate=CertificationGate.SAMPLE_SIZE,
                observed=performance.sample_size,
                required=profile.minimum_sample_size,
                margin=max(1, round(
                    profile.minimum_sample_size
                    * profile.conditional_margin
                )),
            ),
            self._minimum_gate(
                gate=CertificationGate.PERFORMANCE,
                observed=performance.score,
                required=profile.minimum_performance_score,
                margin=profile.conditional_margin,
            ),
            self._optional_minimum_gate(
                gate=CertificationGate.DIRECTION,
                observed=performance.directional_accuracy,
                required=profile.minimum_directional_accuracy,
                required_flag=profile.require_directional_accuracy,
                margin=profile.conditional_margin,
            ),
            self._coverage_gate(
                performance=performance,
                profile=profile,
            ),
            self._minimum_gate(
                gate=CertificationGate.REPUTATION,
                observed=learning.new_reputation,
                required=profile.minimum_reputation,
                margin=profile.conditional_margin,
            ),
            self._maximum_gate(
                gate=CertificationGate.DRIFT,
                observed=drift.drift_score,
                required=profile.maximum_drift_score,
                margin=profile.conditional_margin,
            ),
            CertificationGateResult(
                gate=CertificationGate.ELIGIBILITY,
                passed=performance.eligible,
                conditional=False,
                observed_value=performance.eligible,
                required_value=True,
                explanation=(
                    "Performance scorecard eligibility is "
                    f"{performance.eligible}."
                ),
            ),
        )

        failed = tuple(item for item in gates if not item.passed and not item.conditional)
        conditional = tuple(item for item in gates if item.conditional)

        if failed:
            status = CertificationStatus.REJECTED
        elif conditional:
            status = CertificationStatus.CONDITIONAL
        else:
            status = CertificationStatus.CERTIFIED

        score = sum(
            1.0 if item.passed else 0.5 if item.conditional else 0.0
            for item in gates
        ) / len(gates)

        reasons = tuple(
            item.explanation
            for item in failed + conditional
        )
        restrictions = self._restrictions(
            status=status,
            conditional_gates=conditional,
            drift=drift,
        )

        certification_id = self._certification_id(
            model_key=performance.group_key,
            effective_date=effective_date,
            status=status,
        )

        return ForecastCertificationRecord(
            certification_id=certification_id,
            model_key=performance.group_key,
            status=status,
            certified_at=datetime.now(timezone.utc),
            effective_date=effective_date,
            expires_on=effective_date
            + timedelta(days=profile.validity_days),
            gates=gates,
            score=score,
            reasons=reasons,
            restrictions=restrictions,
            metadata={
                **dict(profile.metadata),
                "performance_grade": performance.grade.value,
                "learning_status": learning.status.value,
                "drift_severity": drift.severity.value,
                "drift_recommendation": drift.recommendation.value,
            },
        )

    @staticmethod
    def _minimum_gate(
        *,
        gate: CertificationGate,
        observed: float | int,
        required: float | int,
        margin: float | int,
    ) -> CertificationGateResult:
        passed = observed >= required
        conditional = (
            not passed
            and observed >= required - margin
        )
        return CertificationGateResult(
            gate=gate,
            passed=passed,
            conditional=conditional,
            observed_value=observed,
            required_value=required,
            explanation=(
                f"{gate.value} observed {observed}; "
                f"minimum required {required}."
            ),
        )

    @staticmethod
    def _optional_minimum_gate(
        *,
        gate: CertificationGate,
        observed: float | None,
        required: float,
        required_flag: bool,
        margin: float,
    ) -> CertificationGateResult:
        if observed is None:
            return CertificationGateResult(
                gate=gate,
                passed=not required_flag,
                conditional=False,
                observed_value=None,
                required_value=required,
                explanation=(
                    f"{gate.value} is unavailable and "
                    f"required={required_flag}."
                ),
            )
        return ForecastCertificationEngine._minimum_gate(
            gate=gate,
            observed=observed,
            required=required,
            margin=margin,
        )

    @staticmethod
    def _coverage_gate(
        *,
        performance: ForecastPerformanceMetrics,
        profile: ForecastCertificationProfile,
    ) -> CertificationGateResult:
        gap = performance.interval_coverage_gap
        if gap is None:
            return CertificationGateResult(
                gate=CertificationGate.CALIBRATION,
                passed=not profile.require_interval_coverage,
                conditional=False,
                observed_value=None,
                required_value=profile.maximum_interval_coverage_gap,
                explanation=(
                    "Interval coverage is unavailable and "
                    f"required={profile.require_interval_coverage}."
                ),
            )

        observed = abs(gap)
        passed = observed <= profile.maximum_interval_coverage_gap
        conditional = (
            not passed
            and observed
            <= profile.maximum_interval_coverage_gap
            + profile.conditional_margin
        )
        return CertificationGateResult(
            gate=CertificationGate.CALIBRATION,
            passed=passed,
            conditional=conditional,
            observed_value=observed,
            required_value=profile.maximum_interval_coverage_gap,
            explanation=(
                f"Absolute interval-coverage gap is {observed:.6f}; "
                f"maximum allowed is "
                f"{profile.maximum_interval_coverage_gap:.6f}."
            ),
        )

    @staticmethod
    def _maximum_gate(
        *,
        gate: CertificationGate,
        observed: float,
        required: float,
        margin: float,
    ) -> CertificationGateResult:
        passed = observed <= required
        conditional = (
            not passed
            and observed <= required + margin
        )
        return CertificationGateResult(
            gate=gate,
            passed=passed,
            conditional=conditional,
            observed_value=observed,
            required_value=required,
            explanation=(
                f"{gate.value} observed {observed:.6f}; "
                f"maximum allowed {required:.6f}."
            ),
        )

    @staticmethod
    def _restrictions(
        *,
        status: CertificationStatus,
        conditional_gates: tuple[CertificationGateResult, ...],
        drift: ForecastDriftSignal,
    ) -> tuple[str, ...]:
        if status is CertificationStatus.REJECTED:
            return ("Model is not approved for production forecasting.",)
        if status is CertificationStatus.CERTIFIED:
            return ()
        restrictions = [
            "Use reduced ensemble weight until all conditional gates pass."
        ]
        restrictions.extend(
            f"Monitor {item.gate.value} during the certification period."
            for item in conditional_gates
        )
        if drift.regime_changed:
            restrictions.append(
                "Restrict deployment to the evaluated regime until "
                "additional evidence is available."
            )
        return tuple(restrictions)

    @staticmethod
    def _certification_id(
        *,
        model_key: str,
        effective_date: date,
        status: CertificationStatus,
    ) -> str:
        payload = (
            f"{model_key}|{effective_date.isoformat()}|{status.value}"
        )
        digest = sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"cert-{digest}"

    @staticmethod
    def _index_performance(
        items: Iterable[ForecastPerformanceMetrics],
    ) -> dict[str, ForecastPerformanceMetrics]:
        values = tuple(items)
        if any(
            item.grouping is not PerformanceGrouping.MODEL
            for item in values
        ):
            raise ValueError(
                "Certification requires model-grouped performance."
            )
        return ForecastCertificationEngine._unique_index(
            values,
            lambda item: item.group_key,
            "performance",
        )

    @staticmethod
    def _index_learning(
        items: Iterable[ModelLearningSignal],
    ) -> dict[str, ModelLearningSignal]:
        return ForecastCertificationEngine._unique_index(
            tuple(items),
            lambda item: item.model_key,
            "learning",
        )

    @staticmethod
    def _index_drift(
        items: Iterable[ForecastDriftSignal],
    ) -> dict[str, ForecastDriftSignal]:
        return ForecastCertificationEngine._unique_index(
            tuple(items),
            lambda item: item.model_key,
            "drift",
        )

    @staticmethod
    def _unique_index(items, key_fn, label: str):
        keys = [key_fn(item) for item in items]
        if len(keys) != len(set(keys)):
            raise ValueError(
                f"Duplicate {label} model keys are not allowed."
            )
        return {key_fn(item): item for item in items}
