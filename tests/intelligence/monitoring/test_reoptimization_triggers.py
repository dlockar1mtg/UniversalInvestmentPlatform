from datetime import datetime, timedelta, timezone

import pytest

from foundation.intelligence.monitoring import (
    AllocationOutcomePlan, DriftCategory, DriftDetectionResult,
    DriftDetectionStatus, DriftSignal, DriftThreshold, MonitoringPolicyBundle,
    ObservedAllocationOutcome, PlannedAllocationOutcome,
    ReoptimizationControlPolicy, ReoptimizationDisposition, TriggerControlState,
    TriggerSeverity, evaluate_reoptimization_trigger, monitor_allocation_outcomes,
)


NOW = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def monitoring_policy(*, cooldown=timedelta(0), hysteresis="0"):
    return MonitoringPolicyBundle(
        "policy-1", (DriftThreshold(DriftCategory.SCORE, "score", 2, 5, 10),),
        cooldown=cooldown, hysteresis_rate=hysteresis,
    )


def signal(identifier, severity):
    return DriftSignal(
        DriftCategory.SCORE, identifier, 80, 70, -10, severity,
        "opp-1", f"{identifier.upper()}_{severity.value}",
    )


def drift(policy, *signals, status=None, fingerprint="d" * 64):
    return DriftDetectionResult(
        "monitor-1", "baseline-1", "window-1", policy.fingerprint,
        status or (
            DriftDetectionStatus.DRIFT_DETECTED if signals
            else DriftDetectionStatus.NO_DRIFT
        ),
        tuple(signals), (), len(signals), fingerprint,
    )


def unplanned_outcomes():
    plan = AllocationOutcomePlan(
        "run-1", "a" * 64, "USD", 1000, 100, 800,
        (PlannedAllocationOutcome("planned", 100, 100),),
    )
    return monitor_allocation_outcomes(
        plan,
        (
            ObservedAllocationOutcome("p", "planned", NOW, 100, 100),
            ObservedAllocationOutcome("x", "unexpected", NOW, 50, 50),
        ),
        observed_protected_capital=100,
        observed_residual_capital=750,
    )


def test_no_material_evidence_returns_no_action():
    policy = monitoring_policy()
    decision = evaluate_reoptimization_trigger(
        "run-1", NOW, drift(policy), policy,
    )
    assert decision.trigger.disposition is ReoptimizationDisposition.NO_ACTION
    assert decision.trigger.severity is TriggerSeverity.NONE
    assert decision.trigger.reason_codes == ("NO_MATERIAL_CHANGE",)
    assert decision.next_state.generation == 0


def test_watch_count_boundary_continues_monitoring_without_reoptimization():
    policy = monitoring_policy()
    decision = evaluate_reoptimization_trigger(
        "run-1", NOW,
        drift(policy, signal("score", TriggerSeverity.WATCH), signal("confidence", TriggerSeverity.WATCH)),
        policy,
        control_policy=ReoptimizationControlPolicy(minimum_watch_signals=2),
    )
    assert decision.trigger.disposition is ReoptimizationDisposition.CONTINUE_MONITORING
    assert decision.trigger.severity is TriggerSeverity.WATCH
    assert decision.drift_signal_count == 2


def test_material_signal_requests_new_run_and_advances_generation():
    policy = monitoring_policy()
    decision = evaluate_reoptimization_trigger(
        "run-1", NOW, drift(policy, signal("score", TriggerSeverity.MATERIAL)), policy,
    )
    assert decision.trigger.disposition is ReoptimizationDisposition.REOPTIMIZE
    assert decision.next_state.last_action_at == NOW
    assert decision.next_state.generation == 1


def test_cooldown_suppresses_duplicate_reoptimization_but_not_critical_escalation():
    policy = monitoring_policy(cooldown=timedelta(hours=12))
    state = TriggerControlState(
        NOW - timedelta(hours=1), TriggerSeverity.MATERIAL, ("SCORE_MATERIAL",), 1,
    )
    suppressed = evaluate_reoptimization_trigger(
        "run-1", NOW, drift(policy, signal("score", TriggerSeverity.MATERIAL)),
        policy, state=state,
    )
    assert suppressed.trigger.disposition is ReoptimizationDisposition.CONTINUE_MONITORING
    assert suppressed.trigger.eligible_at == NOW + timedelta(hours=11)
    assert suppressed.suppressed_reason_codes == ("COOLDOWN_ACTIVE",)

    escalated = evaluate_reoptimization_trigger(
        "run-1", NOW, drift(policy), policy, outcomes=unplanned_outcomes(), state=state,
    )
    assert escalated.trigger.disposition is ReoptimizationDisposition.ESCALATE
    assert escalated.trigger.eligible_at == NOW


def test_hysteresis_preserves_monitoring_after_prior_material_state():
    policy = monitoring_policy(hysteresis="0.10")
    state = TriggerControlState(NOW - timedelta(days=1), TriggerSeverity.MATERIAL, ("SCORE_MATERIAL",), 1)
    decision = evaluate_reoptimization_trigger(
        "run-1", NOW, drift(policy), policy, state=state,
    )
    assert decision.trigger.disposition is ReoptimizationDisposition.CONTINUE_MONITORING
    assert decision.trigger.severity is TriggerSeverity.WATCH
    assert "HYSTERESIS_ACTIVE" in decision.trigger.reason_codes
    assert decision.next_state.generation == 1


def test_decision_is_order_invariant_and_rejects_policy_or_lineage_mismatch():
    policy = monitoring_policy()
    first = evaluate_reoptimization_trigger(
        "run-1", NOW,
        drift(policy, signal("b", TriggerSeverity.MATERIAL), signal("a", TriggerSeverity.WATCH)),
        policy,
    )
    second = evaluate_reoptimization_trigger(
        "run-1", NOW,
        drift(policy, signal("a", TriggerSeverity.WATCH), signal("b", TriggerSeverity.MATERIAL)),
        policy,
    )
    assert first == second
    assert len(first.decision_fingerprint) == 64
    other_policy = MonitoringPolicyBundle(
        "other", (DriftThreshold(DriftCategory.SCORE, "score", 2, 5, 10),),
    )
    with pytest.raises(ValueError, match="fingerprints must match"):
        evaluate_reoptimization_trigger("run-1", NOW, drift(policy), other_policy)
