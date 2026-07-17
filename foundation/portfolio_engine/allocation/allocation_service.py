"""Application service for portfolio allocation calculation."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

from foundation.portfolio_engine.positions import ValuedPosition

from .allocation_calculator import AllocationSummary, calculate_allocation
from .allocation_classifier import classify_positions
from .allocation_repository import AllocationRepository
from .allocation_target_loader import load_allocation_targets


class AllocationService:
    def __init__(
        self,
        repository: AllocationRepository,
        target_file: Path,
    ) -> None:
        self.repository = repository
        self.target_file = target_file

    def calculate_and_store(
        self,
        portfolio_id: UUID,
        positions: list[ValuedPosition],
        *,
        cash_value: Decimal = Decimal("0"),
        include_cash_in_denominator: bool = False,
    ) -> tuple[UUID, AllocationSummary]:
        targets = load_allocation_targets(self.target_file)
        classified = classify_positions(positions)
        summary = calculate_allocation(
            classified,
            targets,
            cash_value=cash_value,
            include_cash_in_denominator=include_cash_in_denominator,
        )
        run_id = self.repository.replace_summary(portfolio_id, summary)
        return run_id, summary
