"""Allocate new contributions toward category deficits."""

from __future__ import annotations

from decimal import Decimal

from foundation.portfolio_engine.allocation import (
    AllocationRow,
    AllocationStatus,
    AllocationTargetConfig,
)
from foundation.portfolio_engine.models import AssetCategory

from .contribution_plan import (
    ContributionPlan,
    ContributionPlanRow,
    ContributionStatus,
)
from .projected_allocation import projected_drift, projected_weight
from .purchase_constraints import apply_purchase_constraints
from .rebalance_policy_loader import RebalancePolicy


def generate_contribution_plan(
    allocation_rows: list[AllocationRow],
    targets: list[AllocationTargetConfig],
    policy: RebalancePolicy,
    *,
    total_contribution: Decimal,
    purchase_increments: dict[AssetCategory, Decimal] | None = None,
) -> ContributionPlan:
    contribution = Decimal(str(total_contribution))
    if contribution < 0:
        raise ValueError("Contribution cannot be negative.")

    target_map = {target.category: target for target in targets}
    row_map = {
        AssetCategory(row.allocation_key): row
        for row in allocation_rows
        if row.allocation_key in {category.value for category in AssetCategory}
    }

    current_total = sum(
        (
            row.market_value
            for row in allocation_rows
            if row.allocation_key != AssetCategory.CASH.value
        ),
        Decimal("0"),
    )
    projected_total = current_total + contribution

    candidates: list[tuple[AllocationTargetConfig, AllocationRow, Decimal]] = []
    for target in targets:
        row = row_map.get(target.category)
        current_value = row.market_value if row else Decimal("0")
        current_weight = (
            Decimal("0") if current_total == 0 else current_value / current_total
        )
        target_value = projected_total * target.target_weight
        deficit = max(target_value - current_value, Decimal("0"))

        synthetic = row or AllocationRow(
            portfolio_id=allocation_rows[0].portfolio_id,
            level=allocation_rows[0].level,
            allocation_key=target.category.value,
            market_value=Decimal("0"),
            actual_weight=current_weight,
            target_weight=target.target_weight,
            minimum_weight=target.minimum_weight,
            maximum_weight=target.maximum_weight,
            percentage_point_drift=current_weight - target.target_weight,
            relative_drift=Decimal("0"),
            target_value=current_total * target.target_weight,
            dollar_variance=-current_total * target.target_weight,
            status=AllocationStatus.UNDERWEIGHT,
            stale_market_value=Decimal("0"),
            unvalued_cost_basis=Decimal("0"),
            position_count=0,
        )
        candidates.append((target, synthetic, deficit))

    if policy.prioritize_most_underweight:
        candidates.sort(
            key=lambda item: (
                item[2],
                -item[0].priority,
            ),
            reverse=True,
        )
    else:
        candidates.sort(key=lambda item: item[0].priority)

    remaining = contribution
    draft_rows: list[tuple[AllocationTargetConfig, AllocationRow, Decimal, Decimal]] = []

    for target, row, deficit in candidates:
        current_weight = (
            Decimal("0") if current_total == 0 else row.market_value / current_total
        )
        if current_weight > target.maximum_weight:
            requested = Decimal("0")
        else:
            requested = min(deficit, remaining)

        draft_rows.append((target, row, deficit, requested))
        remaining -= requested
        if remaining <= 0:
            remaining = Decimal("0")

    final_rows: list[ContributionPlanRow] = []
    total_allocated = Decimal("0")
    retained_total = remaining

    for target, row, deficit, requested in draft_rows:
        increment = (purchase_increments or {}).get(target.category)
        constraint = apply_purchase_constraints(
            requested,
            minimum_purchase_amount=target.minimum_purchase_amount
            if policy.respect_minimum_purchase_amounts
            else Decimal("0"),
            allow_fractional=target.allow_fractional
            if policy.respect_fractional_purchase_rules
            else True,
            purchase_increment=increment,
        )
        recommended = constraint.executable_amount
        retained_total += constraint.retained_amount
        total_allocated += recommended

        projected_value = row.market_value + recommended
        projected_weight_value = projected_weight(
            row.market_value,
            recommended,
            projected_total,
        )
        projected_drift_value = projected_drift(
            row.market_value,
            recommended,
            projected_total,
            target.target_weight,
        )
        remaining_deficit = max(
            projected_total * target.target_weight - projected_value,
            Decimal("0"),
        )

        current_weight = (
            Decimal("0") if current_total == 0 else row.market_value / current_total
        )
        if current_weight > target.maximum_weight:
            status = ContributionStatus.SKIPPED_OVERWEIGHT
            reason = "category_overweight"
        elif deficit <= 0:
            status = ContributionStatus.SKIPPED_NO_DEFICIT
            reason = "no_funding_deficit"
        elif requested > 0 and recommended == 0:
            status = ContributionStatus.BLOCKED_CONSTRAINT
            reason = constraint.reason
        elif recommended < deficit:
            status = ContributionStatus.PARTIALLY_FUNDED
            reason = constraint.reason
        else:
            status = ContributionStatus.FUNDED
            reason = constraint.reason

        final_rows.append(
            ContributionPlanRow(
                category=target.category,
                current_value=row.market_value,
                current_weight=current_weight,
                target_weight=target.target_weight,
                projected_target_value=projected_total * target.target_weight,
                funding_deficit=deficit,
                requested_contribution=requested,
                recommended_contribution=recommended,
                retained_cash=constraint.retained_amount,
                projected_value=projected_value,
                projected_weight=projected_weight_value,
                projected_drift=projected_drift_value,
                remaining_deficit=remaining_deficit,
                status=status,
                constraint_reason=reason,
            )
        )

    return ContributionPlan(
        total_contribution=contribution,
        allocated_contribution=total_allocated,
        unallocated_cash=contribution - total_allocated,
        current_portfolio_value=current_total,
        projected_portfolio_value=projected_total,
        rows=sorted(final_rows, key=lambda row: row.category.value),
    )
