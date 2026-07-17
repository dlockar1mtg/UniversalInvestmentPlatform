"""Application service for contribution-only rebalancing."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

from foundation.portfolio_engine.allocation import (
    AllocationRow,
    load_allocation_targets,
)

from .contribution_allocator import generate_contribution_plan
from .contribution_plan import ContributionPlan
from .rebalance_policy_loader import load_rebalance_policy
from .rebalance_repository import RebalanceRepository


class RebalanceService:
    def __init__(
        self,
        repository: RebalanceRepository,
        target_file: Path,
        policy_file: Path,
    ) -> None:
        self.repository = repository
        self.target_file = target_file
        self.policy_file = policy_file

    def generate_and_store(
        self,
        portfolio_id: UUID,
        allocation_rows: list[AllocationRow],
        *,
        total_contribution: Decimal,
    ) -> tuple[UUID, ContributionPlan]:
        targets = load_allocation_targets(self.target_file)
        policy = load_rebalance_policy(self.policy_file)
        plan = generate_contribution_plan(
            allocation_rows,
            targets,
            policy,
            total_contribution=total_contribution,
        )
        plan_id = self.repository.store_plan(portfolio_id, plan)
        return plan_id, plan
