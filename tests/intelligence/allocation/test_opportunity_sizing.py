from decimal import Decimal

import pytest

from foundation.intelligence.allocation import (
    AllocationBounds, AllocationRequest, CapitalPool, CapitalPoolType
)
from foundation.intelligence.allocation.sizing import (
    SizingInputs, SizingPolicy, SizingReasonCode, SizingStatus,
    size_opportunities, size_opportunity,
)
from foundation.intelligence.allocation.supply import calculate_capital_supply


def request(name="BTC", score=90, bounds=None):
    return AllocationRequest(
        f"req-{name}", name, "ranking-1", score, "P1",
        bounds or AllocationBounds(100, 500, 1000), "crypto", "crypto",
    )


def supply(amount=3000):
    return calculate_capital_supply(CapitalPool("monthly", CapitalPoolType.RECURRING, amount))


def inputs(name="BTC", **kwargs):
    return SizingInputs(
        kwargs.pop("request", request(name)),
        kwargs.pop("confidence_score", 80),
        kwargs.pop("action_strength_score", 70),
        kwargs.pop("portfolio_gap_amount", 900),
        kwargs.pop("opportunity_capacity_amount", 800),
        kwargs.pop("liquidity_capacity_amount", 700),
        kwargs.pop("minimum_purchase_amount", 50),
    )


def test_sizes_target_from_conviction_and_hard_caps():
    result = size_opportunity(inputs(), supply())
    assert result.conviction_factor == Decimal("0.8300")
    assert result.sized_bounds == AllocationBounds(100, Decimal("432.00"), 700)
    assert result.status is SizingStatus.CONSTRAINED
    assert SizingReasonCode.LIQUIDITY_LIMIT in result.reason_codes


def test_purchase_minimum_raises_feasible_minimum():
    result = size_opportunity(inputs(minimum_purchase_amount=250), supply())
    assert result.sized_bounds.minimum_amount == 250
    assert SizingReasonCode.PURCHASE_MINIMUM_APPLIED in result.reason_codes


def test_below_feasible_minimum_is_unsizeable():
    result = size_opportunity(inputs(liquidity_capacity_amount=50), supply())
    assert result.sized_bounds == AllocationBounds(0, 0, 0)
    assert result.status is SizingStatus.UNSIZEABLE
    assert SizingReasonCode.BELOW_FEASIBLE_MINIMUM in result.reason_codes


def test_zero_portfolio_gap_is_unsizeable():
    result = size_opportunity(inputs(portfolio_gap_amount=0), supply())
    assert result.reason_codes == (SizingReasonCode.NO_PORTFOLIO_GAP,)


def test_batch_order_is_deterministic_and_does_not_consume_supply():
    batch = [inputs("SOL"), inputs("BTC")]
    first = size_opportunities(batch, supply(700))
    second = size_opportunities(reversed(batch), supply(700))
    assert first == second
    assert [item.opportunity_id for item in first] == ["BTC", "SOL"]
    assert sum(item.sized_bounds.target_amount for item in first) > 700


def test_rejects_invalid_weights_and_duplicate_opportunities():
    with pytest.raises(ValueError):
        SizingPolicy(priority_weight="0.5", confidence_weight="0.5", action_strength_weight="0.5")
    same = inputs("BTC")
    with pytest.raises(ValueError):
        size_opportunities([same, same], supply())
