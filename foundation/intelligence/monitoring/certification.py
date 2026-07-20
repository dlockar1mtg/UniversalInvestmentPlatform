"""Phase 5.5 monitoring, drift, and reoptimization certification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from .contracts import (
    DriftCategory, DriftThreshold, MonitoringBaseline, MonitoringObservation,
    MonitoringPolicyBundle, MonitoringRunRequest, MonitoringWindow,
    ReoptimizationDisposition,
)
from .orchestrator import MonitoringOrchestrationRequest, run_monitoring_orchestration
from .outcomes import AllocationOutcomePlan, ObservedAllocationOutcome, PlannedAllocationOutcome
from .outputs import build_monitoring_output, validate_monitoring_output
from .triggers import ReoptimizationControlPolicy, TriggerControlState


@dataclass(frozen=True)
class CertificationCheck:
    check_id: str
    status: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        return {"check_id": self.check_id, "evidence": self.evidence, "status": self.status}


@dataclass(frozen=True)
class Phase55CertificationReport:
    phase: str
    status: str
    monitoring_run_id: str
    certification_fingerprint: str
    checks: tuple[CertificationCheck, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "certification_fingerprint": self.certification_fingerprint,
            "checks": [item.to_dict() for item in self.checks],
            "monitoring_run_id": self.monitoring_run_id,
            "phase": self.phase,
            "status": self.status,
        }


def _request(*, reverse: bool = False, score: str = "70") -> MonitoringOrchestrationRequest:
    now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    groups = ("crypto", "etf", "metals", "mtg")
    observations = tuple(
        MonitoringObservation(f"obs-{group}", now + timedelta(hours=2), {"score": score}, group)
        for group in groups
    )
    outcomes = tuple(
        ObservedAllocationOutcome(f"execution-{group}", group, now + timedelta(hours=2), 175, 175)
        for group in groups
    )
    if reverse:
        observations = tuple(reversed(observations))
        outcomes = tuple(reversed(outcomes))
    policy = MonitoringPolicyBundle(
        "phase-5.5-certified-policy",
        (DriftThreshold(DriftCategory.SCORE, "score", 2, 5, 10),),
        cooldown=timedelta(hours=24),
        hysteresis_rate="0.25",
    )
    monitoring = MonitoringRunRequest(
        "phase-5.5-certification", now + timedelta(hours=3),
        MonitoringBaseline("certified-baseline", "phase-5.4-certified-run", "a" * 64, now, {"score": 80}),
        MonitoringWindow("certification-window", now, now + timedelta(hours=3), observations),
        policy,
    )
    plan = AllocationOutcomePlan(
        "phase-5.4-certified-run", "a" * 64, "USD", 1000, 100, 200,
        tuple(PlannedAllocationOutcome(group, 175, 175) for group in groups),
    )
    return MonitoringOrchestrationRequest(
        monitoring, plan, outcomes,
        observed_protected_capital=100, observed_residual_capital=200,
    )


def _check(check_id: str, condition: bool, passed: str, failed: str) -> CertificationCheck:
    return CertificationCheck(check_id, "PASSED" if condition else "FAILED", passed if condition else failed)


def certify_phase_5_5() -> Phase55CertificationReport:
    """Run the deterministic Phase 5.5 certification scenario."""
    request = _request()
    result = run_monitoring_orchestration(request)
    repeated = run_monitoring_orchestration(request)
    reversed_result = run_monitoring_orchestration(_request(reverse=True))
    output = build_monitoring_output(result, indent=None)
    output_valid = True
    try:
        validate_monitoring_output(output)
    except ValueError:
        output_valid = False

    cooldown_request = MonitoringOrchestrationRequest(
        request.monitoring, request.outcome_plan, request.outcome_observations,
        request.observed_protected_capital, request.observed_residual_capital,
        request.outcome_policy, request.control_policy,
        TriggerControlState(request.monitoring.requested_at - timedelta(hours=1)),
    )
    cooldown = run_monitoring_orchestration(cooldown_request)
    escalation_request = MonitoringOrchestrationRequest(
        request.monitoring, request.outcome_plan, request.outcome_observations,
        request.observed_protected_capital, request.observed_residual_capital,
        request.outcome_policy, ReoptimizationControlPolicy(critical_drift_escalates=True),
    )
    escalation = run_monitoring_orchestration(escalation_request)
    groups = {item.opportunity_id for item in result.drift.signals}
    checks = (
        _check("CROSS_ASSET_COVERAGE", groups == {"crypto", "etf", "metals", "mtg"},
               "Certified portfolio groups: crypto, etf, metals, mtg.", "Cross-asset coverage was incomplete."),
        _check("PIPELINE_EXECUTION", len(result.artifacts) == 3,
               "Drift, outcome, trigger control, and unified outputs executed successfully.", "Monitoring pipeline execution was incomplete."),
        _check("DETERMINISM_AND_INPUT_ORDER", result == repeated == reversed_result,
               "Repeated and reversed-input runs produced identical results.", "Monitoring output was not deterministic."),
        _check("DRIFT_BOUNDARY_INTEGRITY", len(result.drift.signals) == 4 and all(item.severity.value == "CRITICAL" for item in result.drift.signals),
               "All four score deltas were classified at the inclusive critical boundary.", "Drift severity boundaries were not preserved."),
        _check("OUTCOME_RECONCILIATION", result.outcomes is not None and result.outcomes.observed_capital_variance == 0,
               "Observed allocations, protected capital, and residual capital reconciled exactly.", "Outcome capital did not reconcile."),
        _check("REOPTIMIZATION_CONTROL", result.result.trigger.disposition is ReoptimizationDisposition.REOPTIMIZE,
               "Material monitoring evidence produced a controlled reoptimization request.", "Material evidence did not trigger reoptimization."),
        _check("COOLDOWN_PROTECTION", cooldown.result.trigger.disposition is ReoptimizationDisposition.CONTINUE_MONITORING and "COOLDOWN_ACTIVE" in cooldown.result.trigger.reason_codes,
               "Cooldown suppressed a duplicate reoptimization while preserving evidence.", "Cooldown protection failed."),
        _check("CRITICAL_ESCALATION", escalation.result.trigger.disposition is ReoptimizationDisposition.ESCALATE,
               "Critical evidence escalated under the certified control policy.", "Critical escalation policy failed."),
        _check("LINEAGE_AND_AUDIT_COMPLETENESS", result.control.source_run_id == "phase-5.4-certified-run" and tuple(item.sequence for item in result.artifacts) == (1, 2, 3),
               "Certified source lineage and all three ordered stage artifacts were preserved.", "Lineage or stage audit evidence was incomplete."),
        _check("UNIFIED_OUTPUT_INTEGRITY", output_valid and len(output.dashboard_rows) == 4 and len(output.audit_rows) >= 11,
               "JSON, dashboard CSV, and audit CSV passed fingerprint and cardinality validation.", "Unified monitoring outputs failed validation."),
    )
    status = "PASSED" if all(item.status == "PASSED" for item in checks) else "FAILED"
    core = {
        "phase": "5.5", "status": status, "monitoring_run_id": request.monitoring.monitoring_run_id,
        "checks": [item.to_dict() for item in checks],
        "monitoring_output_fingerprint": result.result.output_fingerprint,
        "package_fingerprint": output.package_fingerprint,
    }
    fingerprint = sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return Phase55CertificationReport("5.5", status, request.monitoring.monitoring_run_id, fingerprint, checks)
