from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from foundation.portfolio_engine.allocation import (
    AllocationLevel,
    AllocationRow,
    AllocationStatus,
    load_allocation_targets,
)
from foundation.portfolio_engine.rebalancing import (
    generate_contribution_plan,
    load_rebalance_policy,
)


ROOT = Path(__file__).resolve().parents[2]


def _row(category: str, value: str) -> AllocationRow:
    return AllocationRow(
        portfolio_id=uuid4(),
        level=AllocationLevel.CATEGORY,
        allocation_key=category,
        market_value=Decimal(value),
        actual_weight=Decimal("0"),
        target_weight=None,
        minimum_weight=None,
        maximum_weight=None,
        percentage_point_drift=None,
        relative_drift=None,
        target_value=None,
        dollar_variance=None,
        status=AllocationStatus.WITHIN_BAND,
        stale_market_value=Decimal("0"),
        unvalued_cost_basis=Decimal("0"),
        position_count=1,
    )


def test_contribution_plan_allocates_no_more_than_available() -> None:
    rows = [
        _row("crypto", "38000"),
        _row("mtg", "15000"),
        _row("metals", "9000"),
        _row("acorns", "11000"),
        _row("stocks_etfs", "27000"),
    ]
    targets = load_allocation_targets(
        ROOT / "config/portfolios/allocation_targets.yaml"
    )
    policy = load_rebalance_policy(
        ROOT / "config/portfolios/rebalance_policy.yaml"
    )
    plan = generate_contribution_plan(
        rows,
        targets,
        policy,
        total_contribution=Decimal("3000"),
    )
    assert plan.allocated_contribution <= Decimal("3000")
    assert plan.allocated_contribution + plan.unallocated_cash == Decimal("3000")
    crypto = next(row for row in plan.rows if row.category.value == "crypto")
    assert crypto.recommended_contribution == 0
