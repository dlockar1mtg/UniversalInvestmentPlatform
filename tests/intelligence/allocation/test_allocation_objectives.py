from decimal import Decimal

import pytest

from foundation.intelligence.allocation import (
    AllocationBounds, AllocationConstraint, AllocationConstraintType,
    AllocationRequest, CapitalPool, CapitalPoolType,
)
from foundation.intelligence.allocation.constraints import (
    ConstraintContext, evaluate_allocation_constraints,
)
from foundation.intelligence.allocation.objectives import (
    ObjectiveInputs, ObjectivePolicy, ObjectiveStatus,
    calculate_allocation_objective, calculate_allocation_objectives,
)
from foundation.intelligence.allocation.sizing import SizingInputs, size_opportunity
from foundation.intelligence.allocation.supply import calculate_capital_supply


def prepared(name="BTC", priority=90, constraints=(), context=ConstraintContext()):
    request = AllocationRequest(
        f"req-{name}", name, "rank-1", priority, "P1", AllocationBounds(100, 500, 1000),
        "crypto", "crypto",
    )
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, 3000))
    sizing = size_opportunity(SizingInputs(request, 80, 70, 900, 800, 700, 50), supply)
    evaluation = evaluate_allocation_constraints(request, sizing, supply, constraints, context)
    return ObjectiveInputs(request, sizing, evaluation, 85, 75, 90, 80)


def test_calculates_auditable_weighted_utility():
    result = calculate_allocation_objective(prepared())
    assert result.base_utility == Decimal("84.8500")
    assert result.objective_utility == Decimal("84.8500")
    assert result.status is ObjectiveStatus.ACTIVE
    assert sum(item.weighted_value for item in result.contributions) == result.base_utility


def test_soft_binding_constraint_applies_explicit_penalty():
    soft = AllocationConstraint(
        "soft-liquidity", AllocationConstraintType.LIQUIDITY_LIMIT, 200, "BTC", False
    )
    result = calculate_allocation_objective(prepared(constraints=[soft]))
    assert result.penalty_total == Decimal("2.5")
    assert result.objective_utility == result.base_utility - Decimal("2.5")
    assert result.status is ObjectiveStatus.PENALIZED


def test_hard_ineligibility_returns_zero_utility():
    hard = AllocationConstraint(
        "position", AllocationConstraintType.MAXIMUM_POSITION, 50, "BTC", True
    )
    result = calculate_allocation_objective(prepared(constraints=[hard]))
    assert result.objective_utility == 0
    assert result.status is ObjectiveStatus.INELIGIBLE


def test_penalties_are_capped_by_policy():
    rules = [
        AllocationConstraint(f"soft-{i}", AllocationConstraintType.LIQUIDITY_LIMIT, 50, "BTC", False)
        for i in range(5)
    ]
    policy = ObjectivePolicy(maximum_soft_penalty=5)
    result = calculate_allocation_objective(prepared(constraints=rules), policy)
    assert result.penalty_total == 5
    assert len(result.penalties) == 5


def test_batch_order_uses_utility_then_opportunity_id():
    btc = prepared("BTC", 90)
    sol = prepared("SOL", 80)
    first = calculate_allocation_objectives([sol, btc])
    second = calculate_allocation_objectives([btc, sol])
    assert first == second
    assert [result.opportunity_id for result in first] == ["BTC", "SOL"]


def test_rejects_invalid_weights_and_duplicate_opportunities():
    with pytest.raises(ValueError):
        ObjectivePolicy(ranking_weight="0.50")
    same = prepared()
    with pytest.raises(ValueError):
        calculate_allocation_objectives([same, same])
