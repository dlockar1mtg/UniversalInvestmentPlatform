"""Deterministic capital optimization with strict conservation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from typing import Iterable

from .constraints import ConstraintEligibility, ConstraintEvaluation
from .contracts import (
    AllocationLine,
    AllocationReasonCode,
    AllocationRequest,
    AllocationStatus,
    CapitalAllocationResult,
)
from .objectives import AllocationObjectiveResult, ObjectiveStatus
from .supply import CapitalSupplyResult


def _positive(value, name: str) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or converted <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return converted


def _floor_to_quantum(value: Decimal, quantum: Decimal) -> Decimal:
    return (value / quantum).to_integral_value(rounding=ROUND_FLOOR) * quantum


@dataclass(frozen=True)
class OptimizationCandidate:
    request: AllocationRequest
    constraints: ConstraintEvaluation
    objective: AllocationObjectiveResult

    def __post_init__(self) -> None:
        ids = {
            self.request.request_id,
            self.constraints.request_id,
            self.objective.request_id,
        }
        opportunities = {
            self.request.opportunity_id,
            self.constraints.opportunity_id,
            self.objective.opportunity_id,
        }
        if len(ids) != 1 or len(opportunities) != 1:
            raise ValueError("candidate request, constraints, and objective must match")


@dataclass(frozen=True)
class OptimizerPolicy:
    money_quantum: Decimal | float | int | str = Decimal("0.01")

    def __post_init__(self) -> None:
        object.__setattr__(self, "money_quantum", _positive(self.money_quantum, "money_quantum"))


@dataclass(frozen=True)
class CapitalOptimizationResult:
    capital_result: CapitalAllocationResult
    objective_value: Decimal
    allocation_order: tuple[str, ...]
    unfunded_minimum_ids: tuple[str, ...]


def optimize_capital(
    allocation_batch_id: str,
    ranking_batch_id: str,
    supply: CapitalSupplyResult,
    candidates: Iterable[OptimizationCandidate],
    policy: OptimizerPolicy = OptimizerPolicy(),
    *,
    created_at: datetime | None = None,
) -> CapitalOptimizationResult:
    """Allocate deployable capital in minimum, target, then maximum passes."""
    if not allocation_batch_id.strip() or not ranking_batch_id.strip():
        raise ValueError("allocation_batch_id and ranking_batch_id must not be blank")
    materialized = tuple(candidates)
    ids = [candidate.request.opportunity_id for candidate in materialized]
    if len(ids) != len(set(ids)):
        raise ValueError("opportunity_id values must be unique within an optimization batch")
    if any(candidate.request.ranking_batch_id != ranking_batch_id for candidate in materialized):
        raise ValueError("every request must belong to ranking_batch_id")
    if any(candidate.request.currency != supply.currency for candidate in materialized):
        raise ValueError("candidate currency must match the capital supply currency")

    ordered = tuple(
        sorted(
            materialized,
            key=lambda candidate: (
                -candidate.objective.objective_utility,
                candidate.request.opportunity_id,
            ),
        )
    )
    allocations = {candidate.request.opportunity_id: Decimal("0") for candidate in ordered}
    remaining = _floor_to_quantum(supply.deployable_capital, policy.money_quantum)
    active: list[OptimizationCandidate] = []
    unfunded_minimum: list[str] = []

    for candidate in ordered:
        eligible = (
            candidate.constraints.eligibility is not ConstraintEligibility.INELIGIBLE
            and candidate.objective.status is not ObjectiveStatus.INELIGIBLE
            and candidate.objective.objective_utility > 0
            and candidate.constraints.effective_bounds.maximum_amount > 0
        )
        if not eligible:
            continue
        minimum = candidate.constraints.effective_bounds.minimum_amount
        if minimum == 0:
            active.append(candidate)
        elif remaining >= minimum:
            allocations[candidate.request.opportunity_id] = minimum
            remaining -= minimum
            active.append(candidate)
        else:
            unfunded_minimum.append(candidate.request.opportunity_id)

    def fund_to(bound_name: str) -> None:
        nonlocal remaining
        for candidate in active:
            if remaining < policy.money_quantum:
                break
            opportunity_id = candidate.request.opportunity_id
            bound = getattr(candidate.constraints.effective_bounds, bound_name)
            demand = max(Decimal("0"), bound - allocations[opportunity_id])
            addition = _floor_to_quantum(min(demand, remaining), policy.money_quantum)
            allocations[opportunity_id] += addition
            remaining -= addition

    fund_to("target_amount")
    fund_to("maximum_amount")

    lines: list[AllocationLine] = []
    objective_value = Decimal("0")
    for candidate in ordered:
        opportunity_id = candidate.request.opportunity_id
        bounds = candidate.constraints.effective_bounds
        allocated = allocations[opportunity_id]
        if candidate.constraints.eligibility is ConstraintEligibility.INELIGIBLE or candidate.objective.status is ObjectiveStatus.INELIGIBLE:
            status = AllocationStatus.EXCLUDED
            reasons = (AllocationReasonCode.NOT_SELECTED_FOR_ALLOCATION,)
        elif allocated == 0:
            status = AllocationStatus.DEFERRED
            reasons = (
                (AllocationReasonCode.BELOW_MINIMUM_PURCHASE,)
                if opportunity_id in unfunded_minimum
                else (AllocationReasonCode.CAPITAL_EXHAUSTED,)
            )
        elif allocated < bounds.target_amount:
            status = AllocationStatus.PARTIALLY_ALLOCATED
            reasons = (AllocationReasonCode.PARTIAL_CAPITAL_LIMIT,)
        else:
            status = AllocationStatus.ALLOCATED
            reasons = (AllocationReasonCode.TARGET_FUNDED,)
        lines.append(
            AllocationLine(
                candidate.request.request_id,
                opportunity_id,
                bounds.maximum_amount,
                allocated,
                status,
                reasons,
                candidate.constraints.binding_constraint_ids,
                {
                    "objective_utility": str(candidate.objective.objective_utility),
                    "effective_minimum": str(bounds.minimum_amount),
                    "effective_target": str(bounds.target_amount),
                    "effective_maximum": str(bounds.maximum_amount),
                },
            )
        )
        objective_value += allocated * candidate.objective.objective_utility / Decimal("100")

    allocated_total = sum((line.allocated_amount for line in lines), Decimal("0"))
    residual = supply.deployable_capital - allocated_total
    capital_result = CapitalAllocationResult(
        allocation_batch_id,
        ranking_batch_id,
        supply.pool_id,
        supply.gross_capital,
        supply.unavailable_capital + supply.reserved_capital,
        allocated_total,
        residual,
        tuple(lines),
        created_at or datetime.now(timezone.utc),
    )
    return CapitalOptimizationResult(
        capital_result,
        objective_value.quantize(Decimal("0.0001")),
        tuple(candidate.request.opportunity_id for candidate in ordered),
        tuple(unfunded_minimum),
    )
