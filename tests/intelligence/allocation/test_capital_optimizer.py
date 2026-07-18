from decimal import Decimal
from datetime import datetime, timezone

import pytest

from foundation.intelligence.allocation import (
    AllocationBounds, AllocationRequest, CapitalPool, CapitalPoolType,
)
from foundation.intelligence.allocation.constraints import evaluate_allocation_constraints
from foundation.intelligence.allocation.objectives import (
    ObjectiveInputs, calculate_allocation_objective,
)
from foundation.intelligence.allocation.optimizer import (
    OptimizationCandidate, OptimizerPolicy, optimize_capital,
)
from foundation.intelligence.allocation.sizing import SizingInputs, size_opportunity
from foundation.intelligence.allocation.supply import ReserveRule, ReserveType, calculate_capital_supply


def candidate(name, priority, supply, minimum=100, target=400, maximum=700, cap=700):
    request = AllocationRequest(
        f"req-{name}", name, "rank-1", priority, "P1",
        AllocationBounds(minimum, target, maximum), "crypto", "crypto",
    )
    sizing = size_opportunity(
        SizingInputs(request, 80, 70, maximum, cap, maximum, minimum), supply
    )
    constraints = evaluate_allocation_constraints(request, sizing, supply, [])
    objective = calculate_allocation_objective(
        ObjectiveInputs(request, sizing, constraints, 85, 75, 90, 80)
    )
    return OptimizationCandidate(request, constraints, objective)


def test_minimum_target_maximum_passes_and_capital_conservation():
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, 1000))
    result = optimize_capital(
        "allocation-1", "rank-1", supply,
        [candidate("BTC", 90, supply), candidate("SOL", 80, supply)],
    )
    lines = {line.opportunity_id: line for line in result.capital_result.lines}
    assert lines["BTC"].allocated_amount == Decimal("666.00")
    assert lines["SOL"].allocated_amount == Decimal("334.00")
    assert result.capital_result.residual_capital == 0
    assert result.capital_result.gross_capital == (
        result.capital_result.reserved_capital
        + result.capital_result.allocated_capital
        + result.capital_result.residual_capital
    )


def test_never_creates_subminimum_purchase():
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, 300))
    large = candidate("BTC", 95, supply, minimum=250, target=300, maximum=300, cap=300)
    small = candidate("GLD", 80, supply, minimum=100, target=200, maximum=300, cap=300)
    result = optimize_capital("allocation-1", "rank-1", supply, [large, small])
    lines = {line.opportunity_id: line for line in result.capital_result.lines}
    assert lines["BTC"].allocated_amount == 300
    assert lines["GLD"].allocated_amount == 0
    assert result.unfunded_minimum_ids == ("GLD",)


def test_reserved_and_unavailable_capital_are_never_spent():
    pool = CapitalPool("monthly", CapitalPoolType.RECURRING, 1000, 200)
    supply = calculate_capital_supply(
        pool, [ReserveRule("dry", ReserveType.STRATEGIC_DRY_POWDER, fixed_amount=100)],
        unavailable_capital=100,
    )
    result = optimize_capital(
        "allocation-1", "rank-1", supply, [candidate("BTC", 90, supply, maximum=1000, cap=1000)]
    )
    assert result.capital_result.allocated_capital <= 600
    assert result.capital_result.reserved_capital == 400


def test_input_order_is_invariant():
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, 700))
    candidates = [candidate("SOL", 80, supply), candidate("BTC", 90, supply)]
    timestamp = datetime(2026, 7, 18, tzinfo=timezone.utc)
    first = optimize_capital("allocation-1", "rank-1", supply, candidates, created_at=timestamp)
    second = optimize_capital("allocation-1", "rank-1", supply, reversed(candidates), created_at=timestamp)
    assert first == second
    assert first.allocation_order == ("BTC", "SOL")


def test_money_quantum_preserves_unspendable_residual():
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, "100.05"))
    item = candidate("BTC", 90, supply, minimum=0, target=100, maximum="100.05", cap="100.05")
    result = optimize_capital(
        "allocation-1", "rank-1", supply, [item], OptimizerPolicy(money_quantum="0.10")
    )
    assert result.capital_result.allocated_capital == Decimal("100.00")
    assert result.capital_result.residual_capital == Decimal("0.05")


def test_rejects_duplicate_opportunities_and_currency_mismatch():
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, 1000))
    same = candidate("BTC", 90, supply)
    with pytest.raises(ValueError):
        optimize_capital("allocation-1", "rank-1", supply, [same, same])
    euro_request = AllocationRequest(
        "req-EUR", "EUR-ASSET", "rank-1", 80, "P1", AllocationBounds(1, 2, 3),
        "etf", "etf", "EUR",
    )
    sizing = size_opportunity(SizingInputs(euro_request, 80, 80, 3, 3, 3, 1), supply)
    constraints = evaluate_allocation_constraints(euro_request, sizing, supply, [])
    objective = calculate_allocation_objective(ObjectiveInputs(euro_request, sizing, constraints, 80, 80, 80, 80))
    with pytest.raises(ValueError):
        optimize_capital("allocation-1", "rank-1", supply, [OptimizationCandidate(euro_request, constraints, objective)])
