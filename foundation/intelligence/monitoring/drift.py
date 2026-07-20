"""Deterministic metric drift detection for Phase 5.5."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json

from .contracts import (
    DriftDirection,
    DriftSignal,
    DriftThreshold,
    MonitoringRunRequest,
    TriggerSeverity,
)


class DriftDetectionStatus(str, Enum):
    NO_DRIFT = "NO_DRIFT"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class MissingMetricEvidence:
    metric_name: str
    category: str
    opportunity_id: str | None
    reason_code: str

    def __post_init__(self) -> None:
        if not self.metric_name.strip() or not self.category.strip() or not self.reason_code.strip():
            raise ValueError("missing-metric evidence fields must not be blank")


@dataclass(frozen=True)
class DriftDetectionResult:
    monitoring_run_id: str
    baseline_id: str
    window_id: str
    policy_fingerprint: str
    status: DriftDetectionStatus
    signals: tuple[DriftSignal, ...]
    missing_metrics: tuple[MissingMetricEvidence, ...]
    evaluated_comparisons: int
    detection_fingerprint: str

    def __post_init__(self) -> None:
        if self.evaluated_comparisons < 0:
            raise ValueError("evaluated_comparisons must be non-negative")
        for name in (
            "monitoring_run_id", "baseline_id", "window_id",
            "policy_fingerprint", "detection_fingerprint",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")


_SEVERITY_ORDER = {
    TriggerSeverity.CRITICAL: 0,
    TriggerSeverity.MATERIAL: 1,
    TriggerSeverity.WATCH: 2,
    TriggerSeverity.NONE: 3,
}


def _comparison_magnitude(
    signed_delta: Decimal,
    baseline: Decimal,
    threshold: DriftThreshold,
) -> Decimal:
    if threshold.direction is DriftDirection.INCREASE:
        magnitude = max(Decimal("0"), signed_delta)
    elif threshold.direction is DriftDirection.DECREASE:
        magnitude = max(Decimal("0"), -signed_delta)
    else:
        magnitude = abs(signed_delta)
    if not threshold.relative:
        return magnitude
    denominator = abs(baseline)
    if denominator == 0:
        return Decimal("0") if magnitude == 0 else Decimal("1")
    return magnitude / denominator


def _severity(magnitude: Decimal, threshold: DriftThreshold) -> TriggerSeverity:
    if magnitude >= threshold.critical_delta:
        return TriggerSeverity.CRITICAL
    if magnitude >= threshold.material_delta:
        return TriggerSeverity.MATERIAL
    if magnitude >= threshold.watch_delta:
        return TriggerSeverity.WATCH
    return TriggerSeverity.NONE


def _reason(threshold: DriftThreshold, severity: TriggerSeverity) -> str:
    return f"{threshold.category.value}_{threshold.metric_name.upper()}_{severity.value}"


def _fingerprint(
    request: MonitoringRunRequest,
    status: DriftDetectionStatus,
    signals: tuple[DriftSignal, ...],
    missing: tuple[MissingMetricEvidence, ...],
    comparisons: int,
) -> str:
    payload = {
        "monitoring_run_id": request.monitoring_run_id,
        "baseline_id": request.baseline.baseline_id,
        "window_id": request.window.window_id,
        "policy_fingerprint": request.policy.fingerprint,
        "status": status.value,
        "evaluated_comparisons": comparisons,
        "signals": [
            {
                "category": item.category.value,
                "metric_name": item.metric_name,
                "baseline_value": str(item.baseline_value),
                "observed_value": str(item.observed_value),
                "delta": str(item.delta),
                "severity": item.severity.value,
                "opportunity_id": item.opportunity_id,
                "reason_code": item.reason_code,
            }
            for item in signals
        ],
        "missing_metrics": [
            {
                "metric_name": item.metric_name,
                "category": item.category,
                "opportunity_id": item.opportunity_id,
                "reason_code": item.reason_code,
            }
            for item in missing
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def detect_drift(request: MonitoringRunRequest) -> DriftDetectionResult:
    """Compare latest scoped observations with the immutable baseline."""
    observations = tuple(request.window.observations)
    if len(observations) < request.policy.minimum_observations:
        status = DriftDetectionStatus.INSUFFICIENT_DATA
        signals: tuple[DriftSignal, ...] = ()
        missing: tuple[MissingMetricEvidence, ...] = ()
        fingerprint = _fingerprint(request, status, signals, missing, 0)
        return DriftDetectionResult(
            request.monitoring_run_id, request.baseline.baseline_id,
            request.window.window_id, request.policy.fingerprint, status,
            signals, missing, 0, fingerprint,
        )

    scopes = sorted(
        {item.opportunity_id for item in observations},
        key=lambda value: (value is not None, value or ""),
    )
    thresholds = sorted(request.policy.thresholds, key=lambda item: item.key)
    signals_list: list[DriftSignal] = []
    missing_list: list[MissingMetricEvidence] = []
    comparisons = 0

    for opportunity_id in scopes:
        scoped = tuple(item for item in observations if item.opportunity_id == opportunity_id)
        for threshold in thresholds:
            if threshold.metric_name not in request.baseline.metrics:
                missing_list.append(MissingMetricEvidence(
                    threshold.metric_name, threshold.category.value, opportunity_id,
                    "BASELINE_METRIC_MISSING",
                ))
                continue
            candidates = tuple(
                item for item in scoped if threshold.metric_name in item.metrics
            )
            if not candidates:
                missing_list.append(MissingMetricEvidence(
                    threshold.metric_name, threshold.category.value, opportunity_id,
                    "OBSERVED_METRIC_MISSING",
                ))
                continue
            latest = max(candidates, key=lambda item: (item.observed_at, item.observation_id))
            baseline = request.baseline.metrics[threshold.metric_name]
            observed = latest.metrics[threshold.metric_name]
            delta = observed - baseline
            magnitude = _comparison_magnitude(delta, baseline, threshold)
            severity = _severity(magnitude, threshold)
            comparisons += 1
            if severity is TriggerSeverity.NONE:
                continue
            signals_list.append(DriftSignal(
                threshold.category,
                threshold.metric_name,
                baseline,
                observed,
                delta,
                severity,
                opportunity_id,
                _reason(threshold, severity),
            ))

    signals_list.sort(key=lambda item: (
        _SEVERITY_ORDER[item.severity], item.category.value, item.metric_name,
        item.opportunity_id or "",
    ))
    missing_list.sort(key=lambda item: (
        item.category, item.metric_name, item.opportunity_id or "", item.reason_code,
    ))
    signals = tuple(signals_list)
    missing = tuple(missing_list)
    status = (
        DriftDetectionStatus.DRIFT_DETECTED if signals
        else DriftDetectionStatus.NO_DRIFT
    )
    fingerprint = _fingerprint(request, status, signals, missing, comparisons)
    return DriftDetectionResult(
        request.monitoring_run_id,
        request.baseline.baseline_id,
        request.window.window_id,
        request.policy.fingerprint,
        status,
        signals,
        missing,
        comparisons,
        fingerprint,
    )
