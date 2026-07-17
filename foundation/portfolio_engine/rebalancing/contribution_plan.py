"""Contribution plan domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from foundation.portfolio_engine.models import AssetCategory


class ContributionStatus(StrEnum):
    FUNDED = "funded"
    PARTIALLY_FUNDED = "partially_funded"
    SKIPPED_OVERWEIGHT = "skipped_overweight"
    SKIPPED_NO_DEFICIT = "skipped_no_deficit"
    BLOCKED_CONSTRAINT = "blocked_constraint"


@dataclass(slots=True)
class ContributionPlanRow:
    category: AssetCategory
    current_value: Decimal
    current_weight: Decimal
    target_weight: Decimal
    projected_target_value: Decimal
    funding_deficit: Decimal
    requested_contribution: Decimal
    recommended_contribution: Decimal
    retained_cash: Decimal
    projected_value: Decimal
    projected_weight: Decimal
    projected_drift: Decimal
    remaining_deficit: Decimal
    status: ContributionStatus
    constraint_reason: str


@dataclass(slots=True)
class ContributionPlan:
    total_contribution: Decimal
    allocated_contribution: Decimal
    unallocated_cash: Decimal
    current_portfolio_value: Decimal
    projected_portfolio_value: Decimal
    rows: list[ContributionPlanRow]
