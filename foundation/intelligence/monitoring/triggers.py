"""Reoptimization trigger aggregation, cooldown, and hysteresis controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json

from .contracts import (
    MonitoringPolicyBundle,
    ReoptimizationDisposition,
    ReoptimizationTrigger,
    TriggerSeverity,
)
from .drift import DriftDetectionResult, DriftDetectionStatus
from .outcomes import AllocationOutcomeMonitoringResult, OutcomeMonitoringStatus


@dataclass(frozen=True)
class ReoptimizationControlPolicy:
    minimum_material_signals: int = 1
    minimum_watch_signals: int = 2
    critical_drift_escalates: bool = False
    unplanned_activity_escalates: bool = True
    capital_imbalance_escalates: bool = True
    suppress_reoptimization_during_cooldown: bool = True

    def __post_init__(self) -> None:
        if self.minimum_material_signals < 1 or self.minimum_watch_signals < 1:
            raise ValueError("material and watch signal minimums must be positive")


@dataclass(frozen=True)
class TriggerControlState:
    last_action_at: datetime | None = None
    active_severity: TriggerSeverity = TriggerSeverity.NONE
    active_reason_codes: tuple[str, ...] = ()
    generation: int = 0

    def __post_init__(self) -> None:
        if self.last_action_at is not None and self.last_action_at.tzinfo is None:
            raise ValueError("last_action_at must be timezone-aware")
        if self.generation < 0:
            raise ValueError("generation must be non-negative")


@dataclass(frozen=True)
class TriggerControlDecision:
    source_run_id: str
    evaluated_at: datetime
    trigger: ReoptimizationTrigger
    drift_signal_count: int
    outcome_alert_count: int
    contributing_reason_codes: tuple[str, ...]
    suppressed_reason_codes: tuple[str, ...]
    next_state: TriggerControlState
    decision_fingerprint: str

    def __post_init__(self) -> None:
        if not self.source_run_id.strip() or not self.decision_fingerprint.strip():
            raise ValueError("source_run_id and decision_fingerprint must not be blank")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")


_SEVERITY_RANK = {
    TriggerSeverity.NONE: 0,
    TriggerSeverity.WATCH: 1,
    TriggerSeverity.MATERIAL: 2,
    TriggerSeverity.CRITICAL: 3,
}


def _max_severity(values) -> TriggerSeverity:
    return max(values, key=lambda item: _SEVERITY_RANK[item], default=TriggerSeverity.NONE)


def _outcome_evidence(result: AllocationOutcomeMonitoringResult | None):
    if result is None:
        return (), (), False, False
    reasons: list[str] = []
    severities: list[TriggerSeverity] = []
    unplanned = False
    for line in result.lines:
        if line.status is OutcomeMonitoringStatus.ON_TRACK:
            continue
        if line.status is OutcomeMonitoringStatus.UNPLANNED_ACTIVITY:
            severity = TriggerSeverity.CRITICAL
            unplanned = True
        else:
            severity = TriggerSeverity.MATERIAL
        severities.append(severity)
        reasons.extend(reason.value for reason in line.reason_codes)
    capital_imbalance = result.observed_capital_variance != 0
    if capital_imbalance:
        severities.append(TriggerSeverity.CRITICAL)
        reasons.append("OBSERVED_CAPITAL_IMBALANCE")
    return tuple(severities), tuple(reasons), unplanned, capital_imbalance


def evaluate_reoptimization_trigger(
    source_run_id: str,
    evaluated_at: datetime,
    drift: DriftDetectionResult,
    monitoring_policy: MonitoringPolicyBundle,
    *,
    outcomes: AllocationOutcomeMonitoringResult | None = None,
    state: TriggerControlState = TriggerControlState(),
    control_policy: ReoptimizationControlPolicy = ReoptimizationControlPolicy(),
) -> TriggerControlDecision:
    """Convert monitoring evidence into one controlled reoptimization disposition."""
    if not source_run_id.strip():
        raise ValueError("source_run_id must not be blank")
    if evaluated_at.tzinfo is None:
        raise ValueError("evaluated_at must be timezone-aware")
    if drift.policy_fingerprint != monitoring_policy.fingerprint:
        raise ValueError("drift result and monitoring policy fingerprints must match")
    if outcomes is not None and outcomes.source_run_id != source_run_id:
        raise ValueError("outcome monitoring source_run_id must match")

    drift_reasons = tuple(item.reason_code for item in drift.signals)
    drift_severities = tuple(item.severity for item in drift.signals)
    outcome_severities, outcome_reasons, unplanned, capital_imbalance = _outcome_evidence(outcomes)
    all_severities = (*drift_severities, *outcome_severities)
    reasons = tuple(sorted(set((*drift_reasons, *outcome_reasons))))
    critical_count = sum(item is TriggerSeverity.CRITICAL for item in all_severities)
    material_count = sum(
        item in {TriggerSeverity.MATERIAL, TriggerSeverity.CRITICAL}
        for item in all_severities
    )
    watch_count = sum(
        item in {TriggerSeverity.WATCH, TriggerSeverity.MATERIAL, TriggerSeverity.CRITICAL}
        for item in all_severities
    )
    severity = _max_severity(all_severities)
    suppressed: list[str] = []

    escalate = (
        (unplanned and control_policy.unplanned_activity_escalates)
        or (capital_imbalance and control_policy.capital_imbalance_escalates)
        or (critical_count > 0 and control_policy.critical_drift_escalates)
    )
    if escalate:
        disposition = ReoptimizationDisposition.ESCALATE
    elif critical_count > 0 or material_count >= control_policy.minimum_material_signals:
        disposition = ReoptimizationDisposition.REOPTIMIZE
    elif watch_count >= control_policy.minimum_watch_signals:
        disposition = ReoptimizationDisposition.CONTINUE_MONITORING
    else:
        disposition = ReoptimizationDisposition.NO_ACTION

    if drift.status is DriftDetectionStatus.INSUFFICIENT_DATA and not all_severities:
        reasons = ("INSUFFICIENT_MONITORING_DATA",)
        disposition = ReoptimizationDisposition.CONTINUE_MONITORING
        severity = TriggerSeverity.WATCH

    eligible_at = evaluated_at
    cooldown_end = (
        state.last_action_at + monitoring_policy.cooldown
        if state.last_action_at is not None else evaluated_at
    )
    if (
        disposition is ReoptimizationDisposition.REOPTIMIZE
        and control_policy.suppress_reoptimization_during_cooldown
        and evaluated_at < cooldown_end
    ):
        disposition = ReoptimizationDisposition.CONTINUE_MONITORING
        eligible_at = cooldown_end
        suppressed.append("COOLDOWN_ACTIVE")

    if (
        disposition is ReoptimizationDisposition.NO_ACTION
        and monitoring_policy.hysteresis_rate > 0
        and state.active_severity in {TriggerSeverity.MATERIAL, TriggerSeverity.CRITICAL}
    ):
        disposition = ReoptimizationDisposition.CONTINUE_MONITORING
        severity = TriggerSeverity.WATCH
        suppressed.append("HYSTERESIS_ACTIVE")

    if not reasons:
        reasons = (
            state.active_reason_codes
            if "HYSTERESIS_ACTIVE" in suppressed and state.active_reason_codes
            else ("NO_MATERIAL_CHANGE",)
        )
    trigger_reasons = tuple(sorted(set((*reasons, *suppressed))))
    trigger = ReoptimizationTrigger(
        disposition, severity, trigger_reasons, eligible_at, source_run_id,
    )
    action_taken = disposition in {
        ReoptimizationDisposition.REOPTIMIZE,
        ReoptimizationDisposition.ESCALATE,
    }
    next_state = TriggerControlState(
        evaluated_at if action_taken else state.last_action_at,
        severity,
        reasons,
        state.generation + (1 if action_taken else 0),
    )
    payload = {
        "source_run_id": source_run_id,
        "evaluated_at": evaluated_at.isoformat(),
        "policy_fingerprint": monitoring_policy.fingerprint,
        "drift_fingerprint": drift.detection_fingerprint,
        "outcome_fingerprint": outcomes.result_fingerprint if outcomes else None,
        "trigger": {
            "disposition": trigger.disposition.value,
            "severity": trigger.severity.value,
            "reason_codes": trigger.reason_codes,
            "eligible_at": trigger.eligible_at.isoformat(),
        },
        "drift_signal_count": len(drift.signals),
        "outcome_alert_count": len(outcome_severities),
        "contributing_reason_codes": reasons,
        "suppressed_reason_codes": tuple(suppressed),
        "next_state": {
            "last_action_at": next_state.last_action_at.isoformat() if next_state.last_action_at else None,
            "active_severity": next_state.active_severity.value,
            "active_reason_codes": next_state.active_reason_codes,
            "generation": next_state.generation,
        },
    }
    fingerprint = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TriggerControlDecision(
        source_run_id, evaluated_at, trigger, len(drift.signals),
        len(outcome_severities), reasons, tuple(suppressed), next_state, fingerprint,
    )
