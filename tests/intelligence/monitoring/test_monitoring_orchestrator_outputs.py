from dataclasses import replace
from datetime import datetime, timedelta, timezone
import csv
import io
import json

import pytest

from foundation.intelligence.monitoring import (
    AllocationOutcomePlan, DriftCategory, DriftThreshold, MonitoringBaseline,
    MonitoringLifecycleStatus, MonitoringObservation, MonitoringOrchestrationRequest,
    MonitoringPolicyBundle, MonitoringRunRequest, MonitoringWindow,
    ObservedAllocationOutcome, PlannedAllocationOutcome, ReoptimizationDisposition,
    build_monitoring_output, run_monitoring_orchestration, validate_monitoring_output,
)


NOW = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def orchestration_request(*, score="80", include_outcomes=True, observation_order=False):
    policy = MonitoringPolicyBundle(
        "policy-1", (DriftThreshold(DriftCategory.SCORE, "score", 2, 5, 10),),
    )
    observations = (
        MonitoringObservation("old", NOW + timedelta(hours=1), {"score": "82"}, "opp-1"),
        MonitoringObservation("new", NOW + timedelta(hours=2), {"score": score}, "opp-1"),
    )
    if observation_order:
        observations = tuple(reversed(observations))
    monitoring = MonitoringRunRequest(
        "monitor-1", NOW + timedelta(hours=3),
        MonitoringBaseline("baseline-1", "run-1", "a" * 64, NOW, {"score": "80"}),
        MonitoringWindow("window-1", NOW, NOW + timedelta(hours=3), observations),
        policy,
    )
    if not include_outcomes:
        return MonitoringOrchestrationRequest(monitoring)
    plan = AllocationOutcomePlan(
        "run-1", "a" * 64, "USD", 1000, 100, 800,
        (PlannedAllocationOutcome("opp-1", 100, 100),),
    )
    actual = "100" if score == "80" else "75"
    residual = "800" if score == "80" else "825"
    outcomes = (
        ObservedAllocationOutcome("execution-old", "opp-1", NOW + timedelta(hours=1), 50, 50),
        ObservedAllocationOutcome("execution-new", "opp-1", NOW + timedelta(hours=2), actual, actual),
    )
    if observation_order:
        outcomes = tuple(reversed(outcomes))
    return MonitoringOrchestrationRequest(
        monitoring, plan, outcomes,
        observed_protected_capital=100,
        observed_residual_capital=residual,
    )


def test_on_track_run_completes_with_three_ordered_stage_artifacts():
    result = run_monitoring_orchestration(orchestration_request())
    assert result.result.status is MonitoringLifecycleStatus.COMPLETED
    assert result.result.trigger.disposition is ReoptimizationDisposition.NO_ACTION
    assert tuple(item.stage for item in result.artifacts) == (
        "DRIFT_DETECTION", "OUTCOME_MONITORING", "TRIGGER_CONTROL",
    )
    assert tuple(item.sequence for item in result.artifacts) == (1, 2, 3)


def test_drift_and_outcome_shortfall_produce_alerted_reoptimization_result():
    result = run_monitoring_orchestration(orchestration_request(score="70"))
    assert result.result.status is MonitoringLifecycleStatus.COMPLETED_WITH_ALERTS
    assert result.result.trigger.disposition is ReoptimizationDisposition.REOPTIMIZE
    assert result.drift.signals[0].severity.value == "CRITICAL"
    assert result.outcomes.lines[0].status.value == "UNDER_EXECUTED"
    assert result.outcomes.observed_capital_variance == 0


def test_monitoring_only_run_skips_outcomes_without_failing():
    result = run_monitoring_orchestration(
        orchestration_request(include_outcomes=False)
    )
    assert result.outcomes is None
    assert result.artifacts[1].status == "SKIPPED"
    assert result.artifacts[1].evidence["reason_code"] == "NO_OUTCOME_PLAN"


def test_orchestration_and_outputs_are_input_order_invariant():
    first = run_monitoring_orchestration(orchestration_request(score="70"))
    second = run_monitoring_orchestration(
        orchestration_request(score="70", observation_order=True)
    )
    assert first == second
    first_output = build_monitoring_output(first, indent=None)
    second_output = build_monitoring_output(second, indent=None)
    assert first_output == second_output


def test_unified_json_dashboard_and_audit_outputs_validate():
    result = run_monitoring_orchestration(orchestration_request(score="70"))
    package = build_monitoring_output(result)
    validate_monitoring_output(package)
    document = json.loads(package.json_text)
    dashboard = tuple(csv.DictReader(io.StringIO(package.dashboard_csv)))
    audit = tuple(csv.DictReader(io.StringIO(package.audit_csv)))
    assert document["schema_version"] == "5.5.5"
    assert document["package_fingerprint"] == package.package_fingerprint
    assert dashboard[0]["opportunity_id"] == "opp-1"
    assert len(audit) == len(package.audit_rows)
    assert [int(item["sequence"]) for item in audit] == list(range(1, len(audit) + 1))


def test_output_tampering_and_source_lineage_mismatch_fail_closed():
    request = orchestration_request()
    result = run_monitoring_orchestration(request)
    package = build_monitoring_output(result)
    tampered = replace(
        package, json_text=package.json_text.replace("COMPLETED", "CORRUPTED", 1)
    )
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        validate_monitoring_output(tampered)
    wrong_plan = replace(request.outcome_plan, source_run_id="different-run")
    with pytest.raises(ValueError, match="source_run_id"):
        replace(request, outcome_plan=wrong_plan)
