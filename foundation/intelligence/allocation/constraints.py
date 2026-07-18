"""Allocation constraint evaluation before optimization."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .contracts import (
    AllocationBounds,
    AllocationConstraint,
    AllocationConstraintType,
    AllocationRequest,
)
from .sizing import OpportunitySizingResult
from .supply import CapitalSupplyResult


def _decimal(value, name: str) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


class ConstraintDisposition(str, Enum):
    PASS = "PASS"
    BINDING = "BINDING"
    VIOLATED = "VIOLATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConstraintEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CONSTRAINED = "CONSTRAINED"
    INELIGIBLE = "INELIGIBLE"


@dataclass(frozen=True)
class ConstraintContext:
    current_position_amount: Decimal | float | int | str = Decimal("0")
    current_asset_class_amount: Decimal | float | int | str = Decimal("0")
    current_group_amount: Decimal | float | int | str = Decimal("0")

    def __post_init__(self) -> None:
        for name in (
            "current_position_amount",
            "current_asset_class_amount",
            "current_group_amount",
        ):
            object.__setattr__(self, name, _decimal(getattr(self, name), name))


@dataclass(frozen=True)
class ConstraintOutcome:
    constraint_id: str
    constraint_type: AllocationConstraintType
    disposition: ConstraintDisposition
    hard_constraint: bool
    limit_amount: Decimal
    current_amount: Decimal
    headroom_amount: Decimal
    applied_maximum: Decimal | None
    evidence: str


@dataclass(frozen=True)
class ConstraintEvaluation:
    request_id: str
    opportunity_id: str
    original_bounds: AllocationBounds
    effective_bounds: AllocationBounds
    eligibility: ConstraintEligibility
    outcomes: tuple[ConstraintOutcome, ...]
    binding_constraint_ids: tuple[str, ...]


_TYPE_ORDER = {value: index for index, value in enumerate(AllocationConstraintType)}


def _applies(constraint: AllocationConstraint, request: AllocationRequest) -> bool:
    if constraint.scope_key == "PORTFOLIO":
        return True
    if constraint.constraint_type is AllocationConstraintType.MAXIMUM_POSITION:
        return constraint.scope_key == request.opportunity_id
    if constraint.constraint_type is AllocationConstraintType.ASSET_CLASS_LIMIT:
        return constraint.scope_key == request.asset_class
    if constraint.constraint_type is AllocationConstraintType.GROUP_LIMIT:
        return constraint.scope_key == request.group_key
    return constraint.scope_key in {request.opportunity_id, request.asset_class, request.group_key}


def evaluate_allocation_constraints(
    request: AllocationRequest,
    sizing: OpportunitySizingResult,
    supply: CapitalSupplyResult,
    constraints: Iterable[AllocationConstraint],
    context: ConstraintContext = ConstraintContext(),
) -> ConstraintEvaluation:
    """Evaluate all rules and calculate hard-constraint-adjusted bounds."""
    if sizing.request_id != request.request_id or sizing.opportunity_id != request.opportunity_id:
        raise ValueError("request and sizing result identifiers must match")
    rules = tuple(constraints)
    ids = [rule.constraint_id for rule in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("constraint_id values must be unique")
    ordered = sorted(rules, key=lambda rule: (_TYPE_ORDER[rule.constraint_type], rule.constraint_id))
    effective_minimum = sizing.sized_bounds.minimum_amount
    effective_maximum = sizing.sized_bounds.maximum_amount
    outcomes: list[ConstraintOutcome] = []

    for rule in ordered:
        if not _applies(rule, request):
            outcomes.append(
                ConstraintOutcome(
                    rule.constraint_id, rule.constraint_type,
                    ConstraintDisposition.NOT_APPLICABLE, rule.hard_constraint,
                    rule.limit_amount, Decimal("0"), Decimal("0"), None,
                    "Constraint scope does not match this opportunity.",
                )
            )
            continue

        if rule.constraint_type is AllocationConstraintType.MINIMUM_PURCHASE:
            current = Decimal("0")
            headroom = rule.limit_amount
            proposed_minimum = max(effective_minimum, rule.limit_amount)
            violates = effective_maximum < proposed_minimum
            disposition = (
                ConstraintDisposition.VIOLATED if violates
                else ConstraintDisposition.BINDING if proposed_minimum > effective_minimum
                else ConstraintDisposition.PASS
            )
            applied = None
            if rule.hard_constraint and not violates:
                effective_minimum = proposed_minimum
            evidence = "Minimum purchase requirement evaluated."
        else:
            if rule.constraint_type is AllocationConstraintType.MAXIMUM_POSITION:
                current = context.current_position_amount
            elif rule.constraint_type is AllocationConstraintType.ASSET_CLASS_LIMIT:
                current = context.current_asset_class_amount
            elif rule.constraint_type is AllocationConstraintType.GROUP_LIMIT:
                current = context.current_group_amount
            elif rule.constraint_type is AllocationConstraintType.CAPITAL_RESERVE:
                current = supply.reserved_capital
            else:
                current = Decimal("0")
            headroom = max(Decimal("0"), rule.limit_amount - current)
            candidate_maximum = min(effective_maximum, headroom)
            disposition = (
                ConstraintDisposition.VIOLATED if headroom < effective_minimum
                else ConstraintDisposition.BINDING if candidate_maximum < effective_maximum
                else ConstraintDisposition.PASS
            )
            applied = candidate_maximum if rule.hard_constraint else None
            if rule.hard_constraint:
                effective_maximum = candidate_maximum
            evidence = "Remaining headroom evaluated against the sized maximum."

        outcomes.append(
            ConstraintOutcome(
                rule.constraint_id,
                rule.constraint_type,
                disposition,
                rule.hard_constraint,
                rule.limit_amount,
                current,
                headroom,
                applied,
                evidence,
            )
        )

    hard_violation = any(
        outcome.hard_constraint and outcome.disposition is ConstraintDisposition.VIOLATED
        for outcome in outcomes
    ) or effective_maximum < effective_minimum
    if hard_violation:
        bounds = AllocationBounds(0, 0, 0)
        eligibility = ConstraintEligibility.INELIGIBLE
    else:
        target = min(max(sizing.sized_bounds.target_amount, effective_minimum), effective_maximum)
        bounds = AllocationBounds(effective_minimum, target, effective_maximum)
        eligibility = (
            ConstraintEligibility.CONSTRAINED
            if bounds != sizing.sized_bounds
            or any(outcome.disposition is ConstraintDisposition.BINDING for outcome in outcomes)
            else ConstraintEligibility.ELIGIBLE
        )
    binding_ids = tuple(
        outcome.constraint_id
        for outcome in outcomes
        if outcome.disposition in {ConstraintDisposition.BINDING, ConstraintDisposition.VIOLATED}
    )
    return ConstraintEvaluation(
        request.request_id,
        request.opportunity_id,
        sizing.sized_bounds,
        bounds,
        eligibility,
        tuple(outcomes),
        binding_ids,
    )
