from decimal import Decimal

import pytest

from foundation.intelligence.allocation import CapitalPool, CapitalPoolType
from foundation.intelligence.allocation.supply import (
    CapitalSupplyStatus,
    ReserveRule,
    ReserveType,
    calculate_capital_supply,
)


def pool(gross=3000, reserve=0):
    return CapitalPool("monthly", CapitalPoolType.RECURRING, gross, reserve)


def test_no_reserves_leaves_all_capital_deployable():
    result = calculate_capital_supply(pool())
    assert result.deployable_capital == Decimal("3000")
    assert result.status is CapitalSupplyStatus.FULLY_DEPLOYABLE


def test_reconciles_unavailable_contractual_required_and_strategic_capital():
    result = calculate_capital_supply(
        pool(reserve=300),
        [
            ReserveRule("dry-powder", ReserveType.STRATEGIC_DRY_POWDER, gross_rate="0.10"),
            ReserveRule("required", ReserveType.REQUIRED, fixed_amount=200),
        ],
        unavailable_capital=100,
    )
    assert result.unavailable_capital == Decimal("100")
    assert result.reserved_capital == Decimal("800.00")
    assert result.deployable_capital == Decimal("2100.00")
    assert [line.reserve_id for line in result.reserve_lines] == [
        "CONTRACTUAL_POOL_RESERVE", "required", "dry-powder"
    ]


def test_rule_applies_minimum_and_maximum_bounds():
    minimum = ReserveRule("minimum", ReserveType.REQUIRED, gross_rate="0.01", minimum_amount=100)
    maximum = ReserveRule("maximum", ReserveType.REQUIRED, gross_rate="0.50", maximum_amount=250)
    result = calculate_capital_supply(pool(1000), [minimum, maximum])
    assert [line.requested_amount for line in result.reserve_lines] == [Decimal("250"), Decimal("100")]


def test_reserves_are_capped_without_creating_negative_deployable_capital():
    result = calculate_capital_supply(
        pool(500),
        [
            ReserveRule("required", ReserveType.REQUIRED, fixed_amount=400),
            ReserveRule("strategic", ReserveType.STRATEGIC_DRY_POWDER, fixed_amount=400),
        ],
        unavailable_capital=100,
    )
    assert result.deployable_capital == 0
    assert result.status is CapitalSupplyStatus.FULLY_RESERVED
    assert result.reserve_lines[-1].applied_amount == 0
    assert result.reserve_lines[-1].capped_by_available_capital


def test_input_order_does_not_change_result():
    rules = [
        ReserveRule("z", ReserveType.REQUIRED, fixed_amount=100),
        ReserveRule("a", ReserveType.STRATEGIC_DRY_POWDER, fixed_amount=100),
    ]
    assert calculate_capital_supply(pool(), rules) == calculate_capital_supply(pool(), reversed(rules))


def test_rejects_invalid_unavailable_capital_and_duplicate_rules():
    with pytest.raises(ValueError):
        calculate_capital_supply(pool(100), unavailable_capital=101)
    duplicate = ReserveRule("same", ReserveType.REQUIRED, fixed_amount=10)
    with pytest.raises(ValueError):
        calculate_capital_supply(pool(), [duplicate, duplicate])
