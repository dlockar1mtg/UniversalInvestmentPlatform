from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.monitoring import (
    AllocationOutcomePlan, ObservedAllocationOutcome, OutcomeMonitoringPolicy,
    OutcomeMonitoringStatus, OutcomeReasonCode, PlannedAllocationOutcome,
    monitor_allocation_outcomes,
)


NOW = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def allocation_plan():
    return AllocationOutcomePlan(
        "run-1", "a" * 64, "USD", 2000, 200, 1000,
        (
            PlannedAllocationOutcome("opp-a", 500, 600, 100, 85),
            PlannedAllocationOutcome("opp-b", 300, 350, 50, 80),
        ),
    )


def observed(identifier, opportunity, executed, position, score=80, hour=1):
    return ObservedAllocationOutcome(
        identifier, opportunity, NOW + timedelta(hours=hour),
        executed, position, score,
    )


def test_plan_enforces_capital_conservation_and_unique_opportunities():
    plan = allocation_plan()
    assert plan.planned_allocation_total == Decimal("800")
    with pytest.raises(ValueError, match="gross = protected"):
        AllocationOutcomePlan(
            "run", "a" * 64, "USD", 2001, 200, 1000, plan.allocations,
        )
    with pytest.raises(ValueError, match="unique"):
        AllocationOutcomePlan(
            "run", "a" * 64, "USD", 2200, 200, 1000,
            (plan.allocations[0], plan.allocations[0]),
        )


def test_matching_execution_positions_and_capital_are_on_track():
    result = monitor_allocation_outcomes(
        allocation_plan(),
        (
            observed("a", "opp-a", 500, 600, 86),
            observed("b", "opp-b", 300, 350, 81),
        ),
        observed_protected_capital=200,
        observed_residual_capital=1000,
    )
    assert all(item.status is OutcomeMonitoringStatus.ON_TRACK for item in result.lines)
    assert result.executed_total == Decimal("800")
    assert result.execution_variance == 0
    assert result.observed_capital_variance == 0


def test_under_execution_and_residual_cash_change_are_measured():
    result = monitor_allocation_outcomes(
        allocation_plan(),
        (
            observed("a", "opp-a", 400, 500),
            observed("b", "opp-b", 300, 350),
        ),
        observed_protected_capital=200,
        observed_residual_capital=1100,
    )
    line = {item.opportunity_id: item for item in result.lines}["opp-a"]
    assert line.status is OutcomeMonitoringStatus.UNDER_EXECUTED
    assert line.execution_variance == Decimal("-100")
    assert line.target_shortfall == Decimal("100")
    assert OutcomeReasonCode.TARGET_SHORTFALL in line.reason_codes
    assert result.residual_capital_variance == Decimal("100")
    assert result.observed_capital_variance == 0


def test_position_mismatch_and_objective_deterioration_are_preserved():
    result = monitor_allocation_outcomes(
        allocation_plan(),
        (
            observed("a", "opp-a", 500, 575, 70),
            observed("b", "opp-b", 300, 350, 81),
        ),
        observed_protected_capital=200,
        observed_residual_capital=1000,
        policy=OutcomeMonitoringPolicy(objective_score_tolerance=5),
    )
    line = result.lines[0]
    assert line.status is OutcomeMonitoringStatus.POSITION_MISMATCH
    assert line.position_variance == Decimal("-25")
    assert line.objective_variance == Decimal("-15")
    assert OutcomeReasonCode.OBJECTIVE_DETERIORATION in line.reason_codes


def test_missing_planned_execution_and_unplanned_activity_are_explicit():
    result = monitor_allocation_outcomes(
        allocation_plan(),
        (
            observed("a", "opp-a", 500, 600),
            observed("x", "unexpected", 50, 50),
        ),
        observed_protected_capital=200,
        observed_residual_capital=950,
    )
    by_id = {item.opportunity_id: item for item in result.lines}
    assert by_id["opp-b"].status is OutcomeMonitoringStatus.NOT_EXECUTED
    assert by_id["unexpected"].status is OutcomeMonitoringStatus.UNPLANNED_ACTIVITY
    assert by_id["unexpected"].reason_codes == (OutcomeReasonCode.UNPLANNED_EXECUTION,)


def test_latest_observation_and_input_order_produce_stable_result():
    values = (
        observed("new-a", "opp-a", 500, 600, hour=2),
        observed("old-a", "opp-a", 450, 550, hour=1),
        observed("b", "opp-b", 300, 350, hour=1),
    )
    first = monitor_allocation_outcomes(
        allocation_plan(), values,
        observed_protected_capital=200, observed_residual_capital=1000,
    )
    second = monitor_allocation_outcomes(
        allocation_plan(), reversed(values),
        observed_protected_capital=200, observed_residual_capital=1000,
    )
    assert first == second
    assert first.lines[0].observation_id == "new-a"
    assert len(first.result_fingerprint) == 64
