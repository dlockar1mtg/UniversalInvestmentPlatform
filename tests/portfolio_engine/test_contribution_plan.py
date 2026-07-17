from decimal import Decimal

from foundation.portfolio_engine.rebalancing.contribution_plan import ContributionPlan


def test_contribution_plan_totals_can_be_reconciled() -> None:
    plan = ContributionPlan(
        total_contribution=Decimal("3000"),
        allocated_contribution=Decimal("2800"),
        unallocated_cash=Decimal("200"),
        current_portfolio_value=Decimal("100000"),
        projected_portfolio_value=Decimal("103000"),
        rows=[],
    )
    assert plan.allocated_contribution + plan.unallocated_cash == plan.total_contribution
