from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.allocation import (
    AllocationBounds, AllocationRequest, CapitalPool, CapitalPoolType,
)
from foundation.intelligence.allocation.constraints import evaluate_allocation_constraints
from foundation.intelligence.allocation.execution import (
    ExecutionAction, ExecutionCadence, ExecutionPlanningPolicy, build_execution_plan,
)
from foundation.intelligence.allocation.objectives import ObjectiveInputs, calculate_allocation_objective
from foundation.intelligence.allocation.optimizer import OptimizationCandidate, optimize_capital
from foundation.intelligence.allocation.sizing import SizingInputs, size_opportunity
from foundation.intelligence.allocation.supply import calculate_capital_supply


def optimized(capital="500"):
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, capital))
    request = AllocationRequest(
        "req-BTC", "BTC", "rank-1", 90, "P1", AllocationBounds(100, 400, 700),
        "crypto", "crypto",
    )
    sizing = size_opportunity(SizingInputs(request, 80, 70, 700, 700, 700, 100), supply)
    constraints = evaluate_allocation_constraints(request, sizing, supply, [])
    objective = calculate_allocation_objective(ObjectiveInputs(request, sizing, constraints, 85, 75, 90, 80))
    candidate = OptimizationCandidate(request, constraints, objective)
    return optimize_capital(
        "allocation-1", "rank-1", supply, [candidate],
        created_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )


def test_immediate_plan_conserves_optimized_purchase():
    optimization = optimized()
    plan = build_execution_plan("plan-1", optimization, date(2026, 7, 18))
    purchases = [item for item in plan.instructions if item.action is ExecutionAction.PURCHASE]
    assert len(purchases) == 1
    assert purchases[0].cadence is ExecutionCadence.IMMEDIATE
    assert plan.purchase_total == optimization.capital_result.allocated_capital


def test_staged_monthly_plan_preserves_cents_and_end_of_month_dates():
    optimization = optimized("100.05")
    policy = ExecutionPlanningPolicy(immediate_fraction="0.5", recurring_periods=2)
    plan = build_execution_plan("plan-1", optimization, date(2026, 1, 31), policy)
    purchases = [item for item in plan.instructions if item.action is ExecutionAction.PURCHASE]
    assert [item.amount for item in purchases] == [Decimal("50.02"), Decimal("25.01"), Decimal("25.02")]
    assert [item.scheduled_date for item in purchases] == [
        date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)
    ]
    assert sum(item.amount for item in purchases) == Decimal("100.05")


def test_weekly_schedule_uses_seven_day_intervals():
    policy = ExecutionPlanningPolicy(
        immediate_fraction=0, recurring_periods=2, recurring_cadence=ExecutionCadence.WEEKLY
    )
    plan = build_execution_plan("plan-1", optimized(200), date(2026, 7, 18), policy)
    purchases = [item for item in plan.instructions if item.action is ExecutionAction.PURCHASE]
    assert [item.scheduled_date for item in purchases] == [date(2026, 7, 25), date(2026, 8, 1)]


def test_residual_capital_creates_hold_cash_instruction():
    optimization = optimized("100.005")
    plan = build_execution_plan("plan-1", optimization, date(2026, 7, 18))
    holds = [item for item in plan.instructions if item.action is ExecutionAction.HOLD_CASH]
    assert len(holds) == 1
    assert holds[0].amount == optimization.capital_result.residual_capital


def test_plan_is_deterministic_for_same_inputs():
    optimization = optimized()
    policy = ExecutionPlanningPolicy(immediate_fraction="0.25", recurring_periods=3)
    first = build_execution_plan("plan-1", optimization, date(2026, 7, 18), policy)
    second = build_execution_plan("plan-1", optimization, date(2026, 7, 18), policy)
    assert first == second
    assert [item.sequence for item in first.instructions] == list(range(1, len(first.instructions) + 1))


def test_rejects_staging_without_periods_and_invalid_cadence():
    with pytest.raises(ValueError):
        ExecutionPlanningPolicy(immediate_fraction="0.5", recurring_periods=0)
    with pytest.raises(ValueError):
        ExecutionPlanningPolicy(recurring_cadence=ExecutionCadence.IMMEDIATE)
