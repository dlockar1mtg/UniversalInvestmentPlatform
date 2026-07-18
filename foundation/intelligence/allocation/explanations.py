"""Human-readable allocation explanations and immutable audit evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Iterable, Mapping

from .constraints import ConstraintEvaluation
from .contracts import AllocationRequest
from .execution import ContributionExecutionPlan, ExecutionAction
from .objectives import AllocationObjectiveResult
from .optimizer import CapitalOptimizationResult
from .sizing import OpportunitySizingResult


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values)})


def _label(value: str) -> str:
    return value.replace("_", " ").strip().title()


@dataclass(frozen=True)
class AllocationAuditInput:
    request: AllocationRequest
    sizing: OpportunitySizingResult
    constraints: ConstraintEvaluation
    objective: AllocationObjectiveResult

    def __post_init__(self) -> None:
        request_ids = {
            self.request.request_id,
            self.sizing.request_id,
            self.constraints.request_id,
            self.objective.request_id,
        }
        opportunity_ids = {
            self.request.opportunity_id,
            self.sizing.opportunity_id,
            self.constraints.opportunity_id,
            self.objective.opportunity_id,
        }
        if len(request_ids) != 1 or len(opportunity_ids) != 1:
            raise ValueError("allocation audit input identifiers must match")


@dataclass(frozen=True)
class AllocationExplanation:
    opportunity_id: str
    headline: str
    summary: str
    allocation_statement: str
    driver_statements: tuple[str, ...]
    constraint_statements: tuple[str, ...]
    execution_statement: str
    audit_evidence: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AllocationAuditArtifact:
    opportunity_id: str
    stage: str
    sequence: int
    evidence: Mapping[str, object]


@dataclass(frozen=True)
class AllocationExplanationAuditResult:
    allocation_batch_id: str
    explanations: tuple[AllocationExplanation, ...]
    artifacts: tuple[AllocationAuditArtifact, ...]
    batch_evidence: Mapping[str, object]


def build_allocation_explanation_audit(
    inputs: Iterable[AllocationAuditInput],
    optimization: CapitalOptimizationResult,
    execution_plan: ContributionExecutionPlan,
    *,
    max_drivers: int = 3,
) -> AllocationExplanationAuditResult:
    """Explain a complete allocation without recalculating any upstream value."""
    if max_drivers < 1:
        raise ValueError("max_drivers must be at least 1")
    materialized = tuple(inputs)
    by_id = {item.request.opportunity_id: item for item in materialized}
    if len(by_id) != len(materialized):
        raise ValueError("opportunity_id values must be unique")
    expected = set(optimization.allocation_order)
    if set(by_id) != expected:
        raise ValueError("audit inputs must match the optimization opportunity set")
    if execution_plan.allocation_batch_id != optimization.capital_result.allocation_batch_id:
        raise ValueError("execution plan must belong to the optimization batch")

    lines = {
        line.opportunity_id: line for line in optimization.capital_result.lines
    }
    execution_by_id: dict[str, list] = {opportunity_id: [] for opportunity_id in expected}
    for instruction in execution_plan.instructions:
        if instruction.opportunity_id in execution_by_id:
            execution_by_id[instruction.opportunity_id].append(instruction)

    explanations: list[AllocationExplanation] = []
    artifacts: list[AllocationAuditArtifact] = []
    sequence = 1
    for opportunity_id in optimization.allocation_order:
        item = by_id[opportunity_id]
        line = lines[opportunity_id]
        bounds = item.constraints.effective_bounds
        allocated = line.allocated_amount
        if line.status.value == "EXCLUDED":
            headline = f"{opportunity_id} excluded from capital allocation"
        elif allocated == 0:
            headline = f"{opportunity_id} deferred with no current allocation"
        elif allocated < bounds.target_amount:
            headline = f"{opportunity_id} partially funded"
        else:
            headline = f"{opportunity_id} target funded"
        reasons = ", ".join(reason.value for reason in line.reason_codes)
        summary = f"Final status: {line.status.value}. Allocation reason: {reasons}."
        allocation_statement = (
            f"Allocated {allocated} {item.request.currency} against minimum "
            f"{bounds.minimum_amount}, target {bounds.target_amount}, and maximum "
            f"{bounds.maximum_amount}; unmet maximum capacity is {line.unmet_amount}."
        )

        drivers = sorted(
            item.objective.contributions,
            key=lambda contribution: (-contribution.weighted_value, contribution.factor_name),
        )[:max_drivers]
        driver_statements = tuple(
            f"{_label(driver.factor_name)} contributed {driver.weighted_value} utility "
            f"from score {driver.raw_score} at weight {driver.weight}."
            for driver in drivers
        )
        constraint_statements = tuple(
            f"{outcome.constraint_id}: {outcome.disposition.value}; headroom "
            f"{outcome.headroom_amount}; hard={str(outcome.hard_constraint).lower()}."
            for outcome in item.constraints.outcomes
            if outcome.constraint_id in item.constraints.binding_constraint_ids
        ) or ("No binding allocation constraints.",)

        instructions = execution_by_id[opportunity_id]
        purchases = [
            instruction for instruction in instructions
            if instruction.action is ExecutionAction.PURCHASE
        ]
        deferred = any(
            instruction.action is ExecutionAction.DEFER for instruction in instructions
        )
        if purchases:
            first_date = min(instruction.scheduled_date for instruction in purchases)
            last_date = max(instruction.scheduled_date for instruction in purchases)
            execution_statement = (
                f"{len(purchases)} purchase instruction(s) totaling "
                f"{sum((instruction.amount for instruction in purchases), Decimal('0'))} "
                f"are scheduled from {first_date.isoformat()} through {last_date.isoformat()}."
            )
        elif deferred:
            execution_statement = "Execution is deferred; no purchase is currently scheduled."
        else:
            execution_statement = "No execution instruction was generated."

        evidence = _freeze(
            {
                "allocated_amount": str(allocated),
                "allocation_status": line.status.value,
                "binding_constraints": tuple(line.binding_constraints),
                "effective_maximum": str(bounds.maximum_amount),
                "effective_minimum": str(bounds.minimum_amount),
                "effective_target": str(bounds.target_amount),
                "objective_utility": str(item.objective.objective_utility),
                "reason_codes": tuple(reason.value for reason in line.reason_codes),
                "unmet_amount": str(line.unmet_amount),
            }
        )
        explanations.append(
            AllocationExplanation(
                opportunity_id,
                headline,
                summary,
                allocation_statement,
                driver_statements,
                constraint_statements,
                execution_statement,
                evidence,
            )
        )

        stage_evidence = (
            (
                "REQUEST",
                {
                    "priority_score": str(item.request.priority_score),
                    "priority_tier": item.request.priority_tier,
                    "requested_bounds": tuple(str(value) for value in (
                        item.request.bounds.minimum_amount,
                        item.request.bounds.target_amount,
                        item.request.bounds.maximum_amount,
                    )),
                },
            ),
            (
                "SIZING",
                {
                    "status": item.sizing.status.value,
                    "conviction_factor": str(item.sizing.conviction_factor),
                    "sized_bounds": tuple(str(value) for value in (
                        item.sizing.sized_bounds.minimum_amount,
                        item.sizing.sized_bounds.target_amount,
                        item.sizing.sized_bounds.maximum_amount,
                    )),
                },
            ),
            (
                "CONSTRAINTS",
                {
                    "eligibility": item.constraints.eligibility.value,
                    "binding_constraint_ids": item.constraints.binding_constraint_ids,
                },
            ),
            (
                "OBJECTIVE",
                {
                    "base_utility": str(item.objective.base_utility),
                    "penalty_total": str(item.objective.penalty_total),
                    "objective_utility": str(item.objective.objective_utility),
                },
            ),
            (
                "OPTIMIZATION",
                {
                    "allocated_amount": str(allocated),
                    "status": line.status.value,
                    "reason_codes": tuple(reason.value for reason in line.reason_codes),
                },
            ),
            (
                "EXECUTION",
                {
                    "instruction_count": len(instructions),
                    "purchase_total": str(sum(
                        (instruction.amount for instruction in purchases), Decimal("0")
                    )),
                },
            ),
        )
        for stage, stage_values in stage_evidence:
            artifacts.append(
                AllocationAuditArtifact(
                    opportunity_id, stage, sequence, _freeze(stage_values)
                )
            )
            sequence += 1

    capital = optimization.capital_result
    batch_evidence = _freeze(
        {
            "allocated_capital": str(capital.allocated_capital),
            "allocation_batch_id": capital.allocation_batch_id,
            "gross_capital": str(capital.gross_capital),
            "objective_value": str(optimization.objective_value),
            "reserved_capital": str(capital.reserved_capital),
            "residual_capital": str(capital.residual_capital),
            "capital_conserved": capital.gross_capital
            == capital.reserved_capital + capital.allocated_capital + capital.residual_capital,
            "execution_purchase_total": str(execution_plan.purchase_total),
            "execution_retained_cash": str(execution_plan.retained_cash),
        }
    )
    return AllocationExplanationAuditResult(
        capital.allocation_batch_id,
        tuple(explanations),
        tuple(artifacts),
        batch_evidence,
    )
