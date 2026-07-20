"""Deterministic monitoring, outcome, and trigger orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping

from .contracts import (
    MonitoringLifecycleStatus,
    MonitoringRunRequest,
    MonitoringRunResult,
    ReoptimizationDisposition,
    TriggerSeverity,
)
from .drift import DriftDetectionResult, detect_drift
from .outcomes import (
    AllocationOutcomeMonitoringResult,
    AllocationOutcomePlan,
    ObservedAllocationOutcome,
    OutcomeMonitoringPolicy,
    OutcomeMonitoringStatus,
    monitor_allocation_outcomes,
)
from .triggers import (
    ReoptimizationControlPolicy,
    TriggerControlDecision,
    TriggerControlState,
    evaluate_reoptimization_trigger,
)


def _amount(value: object | None, name: str) -> Decimal | None:
    if value is None:
        return None
    converted = Decimal(str(value))
    if not converted.is_finite() or converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values, key=str)})


@dataclass(frozen=True)
class MonitoringOrchestrationRequest:
    monitoring: MonitoringRunRequest
    outcome_plan: AllocationOutcomePlan | None = None
    outcome_observations: tuple[ObservedAllocationOutcome, ...] = ()
    observed_protected_capital: Decimal | float | int | str | None = None
    observed_residual_capital: Decimal | float | int | str | None = None
    outcome_policy: OutcomeMonitoringPolicy = field(default_factory=OutcomeMonitoringPolicy)
    control_policy: ReoptimizationControlPolicy = field(default_factory=ReoptimizationControlPolicy)
    control_state: TriggerControlState = field(default_factory=TriggerControlState)

    def __post_init__(self) -> None:
        protected = _amount(self.observed_protected_capital, "observed_protected_capital")
        residual = _amount(self.observed_residual_capital, "observed_residual_capital")
        object.__setattr__(self, "observed_protected_capital", protected)
        object.__setattr__(self, "observed_residual_capital", residual)
        if self.outcome_plan is None:
            if self.outcome_observations or protected is not None or residual is not None:
                raise ValueError("outcome observations and capital require outcome_plan")
        else:
            if self.outcome_plan.source_run_id != self.monitoring.baseline.source_run_id:
                raise ValueError("outcome plan must match baseline source_run_id")
            if protected is None or residual is None:
                raise ValueError("outcome monitoring requires observed protected and residual capital")


@dataclass(frozen=True)
class MonitoringStageArtifact:
    sequence: int
    stage: str
    status: str
    evidence: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.sequence < 1 or not self.stage.strip() or not self.status.strip():
            raise ValueError("stage artifact sequence, stage, and status are required")
        object.__setattr__(self, "evidence", _freeze(self.evidence))


@dataclass(frozen=True)
class MonitoringOrchestrationResult:
    result: MonitoringRunResult
    drift: DriftDetectionResult
    outcomes: AllocationOutcomeMonitoringResult | None
    control: TriggerControlDecision
    artifacts: tuple[MonitoringStageArtifact, ...]


def _fingerprint(
    request: MonitoringOrchestrationRequest,
    drift: DriftDetectionResult,
    outcomes: AllocationOutcomeMonitoringResult | None,
    control: TriggerControlDecision,
    artifacts: tuple[MonitoringStageArtifact, ...],
) -> str:
    payload = {
        "monitoring_run_id": request.monitoring.monitoring_run_id,
        "source_run_id": request.monitoring.baseline.source_run_id,
        "source_output_fingerprint": request.monitoring.baseline.source_output_fingerprint,
        "policy_fingerprint": request.monitoring.policy.fingerprint,
        "drift_fingerprint": drift.detection_fingerprint,
        "outcome_fingerprint": outcomes.result_fingerprint if outcomes else None,
        "control_fingerprint": control.decision_fingerprint,
        "artifacts": [
            {
                "sequence": item.sequence,
                "stage": item.stage,
                "status": item.status,
                "evidence": dict(item.evidence),
            }
            for item in artifacts
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def run_monitoring_orchestration(
    request: MonitoringOrchestrationRequest,
) -> MonitoringOrchestrationResult:
    """Execute drift, optional outcome monitoring, and trigger control atomically."""
    monitoring = request.monitoring
    drift = detect_drift(monitoring)
    artifacts: list[MonitoringStageArtifact] = [
        MonitoringStageArtifact(
            1, "DRIFT_DETECTION", drift.status.value,
            {
                "detection_fingerprint": drift.detection_fingerprint,
                "evaluated_comparisons": drift.evaluated_comparisons,
                "missing_metric_count": len(drift.missing_metrics),
                "signal_count": len(drift.signals),
            },
        )
    ]

    outcomes = None
    if request.outcome_plan is not None:
        outcomes = monitor_allocation_outcomes(
            request.outcome_plan,
            request.outcome_observations,
            observed_protected_capital=request.observed_protected_capital,
            observed_residual_capital=request.observed_residual_capital,
            policy=request.outcome_policy,
        )
        alert_count = sum(
            item.status is not OutcomeMonitoringStatus.ON_TRACK for item in outcomes.lines
        )
        artifacts.append(MonitoringStageArtifact(
            2, "OUTCOME_MONITORING", "ALERTS" if alert_count else "ON_TRACK",
            {
                "alert_count": alert_count,
                "executed_total": str(outcomes.executed_total),
                "execution_variance": str(outcomes.execution_variance),
                "observed_capital_variance": str(outcomes.observed_capital_variance),
                "result_fingerprint": outcomes.result_fingerprint,
            },
        ))
    else:
        artifacts.append(MonitoringStageArtifact(
            2, "OUTCOME_MONITORING", "SKIPPED", {"reason_code": "NO_OUTCOME_PLAN"},
        ))

    control = evaluate_reoptimization_trigger(
        monitoring.baseline.source_run_id,
        monitoring.requested_at,
        drift,
        monitoring.policy,
        outcomes=outcomes,
        state=request.control_state,
        control_policy=request.control_policy,
    )
    artifacts.append(MonitoringStageArtifact(
        3, "TRIGGER_CONTROL", control.trigger.disposition.value,
        {
            "decision_fingerprint": control.decision_fingerprint,
            "eligible_at": control.trigger.eligible_at.isoformat(),
            "reason_codes": control.trigger.reason_codes,
            "severity": control.trigger.severity.value,
            "suppressed_reason_codes": control.suppressed_reason_codes,
        },
    ))
    artifact_tuple = tuple(artifacts)
    fingerprint = _fingerprint(request, drift, outcomes, control, artifact_tuple)
    alerts = (
        control.trigger.severity is not TriggerSeverity.NONE
        or control.trigger.disposition is not ReoptimizationDisposition.NO_ACTION
        or bool(drift.missing_metrics)
    )
    status = (
        MonitoringLifecycleStatus.COMPLETED_WITH_ALERTS
        if alerts else MonitoringLifecycleStatus.COMPLETED
    )
    result = MonitoringRunResult(
        monitoring.monitoring_run_id,
        status,
        monitoring.policy.fingerprint,
        drift.signals,
        control.trigger,
        fingerprint,
    )
    return MonitoringOrchestrationResult(result, drift, outcomes, control, artifact_tuple)
