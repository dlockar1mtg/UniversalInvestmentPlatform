from decimal import Decimal

import pytest

from foundation.intelligence.allocation import (
    AllocationBounds, AllocationConstraint, AllocationConstraintType,
    AllocationRequest, CapitalPool, CapitalPoolType,
)
from foundation.intelligence.allocation.constraints import (
    ConstraintContext, ConstraintDisposition, ConstraintEligibility,
    evaluate_allocation_constraints,
)
from foundation.intelligence.allocation.sizing import SizingInputs, size_opportunity
from foundation.intelligence.allocation.supply import calculate_capital_supply


def setup():
    request = AllocationRequest(
        "req-BTC", "BTC", "rank-1", 90, "P1", AllocationBounds(100, 500, 1000),
        "crypto", "crypto",
    )
    supply = calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, 3000))
    sizing = size_opportunity(SizingInputs(request, 80, 70, 900, 800, 700, 50), supply)
    return request, supply, sizing


def test_position_headroom_constrains_maximum_and_target():
    request, supply, sizing = setup()
    rule = AllocationConstraint(
        "btc-position", AllocationConstraintType.MAXIMUM_POSITION, 500, "BTC"
    )
    result = evaluate_allocation_constraints(
        request, sizing, supply, [rule], ConstraintContext(current_position_amount=200)
    )
    assert result.effective_bounds.maximum_amount == Decimal("300")
    assert result.effective_bounds.target_amount == Decimal("300")
    assert result.eligibility is ConstraintEligibility.CONSTRAINED


def test_minimum_purchase_above_headroom_is_ineligible():
    request, supply, sizing = setup()
    rules = [
        AllocationConstraint("minimum", AllocationConstraintType.MINIMUM_PURCHASE, 400, "BTC"),
        AllocationConstraint("position", AllocationConstraintType.MAXIMUM_POSITION, 250, "BTC"),
    ]
    result = evaluate_allocation_constraints(request, sizing, supply, rules)
    assert result.eligibility is ConstraintEligibility.INELIGIBLE
    assert result.effective_bounds == AllocationBounds(0, 0, 0)


def test_asset_class_and_group_limits_use_current_exposure():
    request, supply, sizing = setup()
    rules = [
        AllocationConstraint("asset", AllocationConstraintType.ASSET_CLASS_LIMIT, 1000, "crypto"),
        AllocationConstraint("group", AllocationConstraintType.GROUP_LIMIT, 900, "crypto"),
    ]
    context = ConstraintContext(current_asset_class_amount=600, current_group_amount=700)
    result = evaluate_allocation_constraints(request, sizing, supply, rules, context)
    assert result.effective_bounds.maximum_amount == 200
    assert set(result.binding_constraint_ids) == {"asset", "group"}


def test_soft_constraint_is_audited_but_does_not_reduce_bounds():
    request, supply, sizing = setup()
    rule = AllocationConstraint(
        "soft-liquidity", AllocationConstraintType.LIQUIDITY_LIMIT, 200, "BTC", False
    )
    result = evaluate_allocation_constraints(request, sizing, supply, [rule])
    assert result.effective_bounds == sizing.sized_bounds
    assert result.outcomes[0].disposition is ConstraintDisposition.BINDING
    assert result.outcomes[0].applied_maximum is None


def test_nonmatching_scope_is_not_applicable():
    request, supply, sizing = setup()
    rule = AllocationConstraint(
        "metals", AllocationConstraintType.ASSET_CLASS_LIMIT, 100, "metals"
    )
    result = evaluate_allocation_constraints(request, sizing, supply, [rule])
    assert result.outcomes[0].disposition is ConstraintDisposition.NOT_APPLICABLE
    assert result.eligibility is ConstraintEligibility.ELIGIBLE


def test_order_is_deterministic_and_duplicate_ids_are_rejected():
    request, supply, sizing = setup()
    rules = [
        AllocationConstraint("z", AllocationConstraintType.GROUP_LIMIT, 600, "crypto"),
        AllocationConstraint("a", AllocationConstraintType.MAXIMUM_POSITION, 600, "BTC"),
    ]
    first = evaluate_allocation_constraints(request, sizing, supply, rules)
    second = evaluate_allocation_constraints(request, sizing, supply, reversed(rules))
    assert first == second
    duplicate = AllocationConstraint("same", AllocationConstraintType.LIQUIDITY_LIMIT, 100, "BTC")
    with pytest.raises(ValueError):
        evaluate_allocation_constraints(request, sizing, supply, [duplicate, duplicate])
