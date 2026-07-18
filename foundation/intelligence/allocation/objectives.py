"""Auditable allocation-objective scoring before optimization."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .constraints import (
    ConstraintDisposition,
    ConstraintEligibility,
    ConstraintEvaluation,
)
from .contracts import AllocationRequest
from .sizing import OpportunitySizingResult


def _number(value, name: str, maximum: Decimal | None = None) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    if maximum is not None and converted > maximum:
        raise ValueError(f"{name} must not exceed {maximum}")
    return converted


class ObjectiveStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENALIZED = "PENALIZED"
    INELIGIBLE = "INELIGIBLE"


@dataclass(frozen=True)
class ObjectiveInputs:
    request: AllocationRequest
    sizing: OpportunitySizingResult
    constraints: ConstraintEvaluation
    target_gap_score: Decimal | float | int | str
    diversification_score: Decimal | float | int | str
    liquidity_score: Decimal | float | int | str
    capital_efficiency_score: Decimal | float | int | str

    def __post_init__(self) -> None:
        if (
            self.request.request_id != self.sizing.request_id
            or self.request.request_id != self.constraints.request_id
        ):
            raise ValueError("request, sizing, and constraint identifiers must match")
        for name in (
            "target_gap_score",
            "diversification_score",
            "liquidity_score",
            "capital_efficiency_score",
        ):
            object.__setattr__(self, name, _number(getattr(self, name), name, Decimal("100")))


@dataclass(frozen=True)
class ObjectivePolicy:
    ranking_weight: Decimal | float | int | str = Decimal("0.35")
    conviction_weight: Decimal | float | int | str = Decimal("0.20")
    target_gap_weight: Decimal | float | int | str = Decimal("0.20")
    diversification_weight: Decimal | float | int | str = Decimal("0.15")
    liquidity_weight: Decimal | float | int | str = Decimal("0.05")
    capital_efficiency_weight: Decimal | float | int | str = Decimal("0.05")
    soft_binding_penalty: Decimal | float | int | str = Decimal("2.5")
    soft_violation_penalty: Decimal | float | int | str = Decimal("5")
    maximum_soft_penalty: Decimal | float | int | str = Decimal("20")

    def __post_init__(self) -> None:
        weight_names = (
            "ranking_weight", "conviction_weight", "target_gap_weight",
            "diversification_weight", "liquidity_weight", "capital_efficiency_weight",
        )
        weights = {name: _number(getattr(self, name), name) for name in weight_names}
        if sum(weights.values(), Decimal("0")) != Decimal("1"):
            raise ValueError("objective weights must sum to 1")
        for name, value in weights.items():
            object.__setattr__(self, name, value)
        for name in ("soft_binding_penalty", "soft_violation_penalty", "maximum_soft_penalty"):
            object.__setattr__(self, name, _number(getattr(self, name), name))


@dataclass(frozen=True)
class ObjectiveContribution:
    factor_name: str
    raw_score: Decimal
    weight: Decimal
    weighted_value: Decimal


@dataclass(frozen=True)
class ObjectivePenalty:
    constraint_id: str
    disposition: ConstraintDisposition
    penalty_value: Decimal


@dataclass(frozen=True)
class AllocationObjectiveResult:
    request_id: str
    opportunity_id: str
    base_utility: Decimal
    penalty_total: Decimal
    objective_utility: Decimal
    status: ObjectiveStatus
    contributions: tuple[ObjectiveContribution, ...]
    penalties: tuple[ObjectivePenalty, ...]
    deterministic_key: tuple[Decimal, str]


def calculate_allocation_objective(
    inputs: ObjectiveInputs,
    policy: ObjectivePolicy = ObjectivePolicy(),
) -> AllocationObjectiveResult:
    """Calculate utility without changing sizing or constraint outcomes."""
    raw_factors = {
        "ranking_priority": inputs.request.priority_score,
        "sizing_conviction": inputs.sizing.conviction_factor * Decimal("100"),
        "target_gap": inputs.target_gap_score,
        "diversification": inputs.diversification_score,
        "liquidity": inputs.liquidity_score,
        "capital_efficiency": inputs.capital_efficiency_score,
    }
    weights = {
        "ranking_priority": policy.ranking_weight,
        "sizing_conviction": policy.conviction_weight,
        "target_gap": policy.target_gap_weight,
        "diversification": policy.diversification_weight,
        "liquidity": policy.liquidity_weight,
        "capital_efficiency": policy.capital_efficiency_weight,
    }
    contributions = tuple(
        ObjectiveContribution(
            name,
            raw_factors[name],
            weights[name],
            (raw_factors[name] * weights[name]).quantize(Decimal("0.0001")),
        )
        for name in sorted(raw_factors)
    )
    base = sum((item.weighted_value for item in contributions), Decimal("0"))

    penalties: list[ObjectivePenalty] = []
    for outcome in inputs.constraints.outcomes:
        if outcome.hard_constraint:
            continue
        if outcome.disposition is ConstraintDisposition.BINDING:
            value = policy.soft_binding_penalty
        elif outcome.disposition is ConstraintDisposition.VIOLATED:
            value = policy.soft_violation_penalty
        else:
            continue
        penalties.append(ObjectivePenalty(outcome.constraint_id, outcome.disposition, value))
    uncapped_penalty = sum((item.penalty_value for item in penalties), Decimal("0"))
    penalty_total = min(uncapped_penalty, policy.maximum_soft_penalty)

    if inputs.constraints.eligibility is ConstraintEligibility.INELIGIBLE:
        utility = Decimal("0")
        status = ObjectiveStatus.INELIGIBLE
    else:
        utility = max(Decimal("0"), base - penalty_total).quantize(Decimal("0.0001"))
        status = ObjectiveStatus.PENALIZED if penalty_total > 0 else ObjectiveStatus.ACTIVE
    return AllocationObjectiveResult(
        inputs.request.request_id,
        inputs.request.opportunity_id,
        base,
        penalty_total,
        utility,
        status,
        contributions,
        tuple(penalties),
        (-utility, inputs.request.opportunity_id),
    )


def calculate_allocation_objectives(
    inputs: Iterable[ObjectiveInputs],
    policy: ObjectivePolicy = ObjectivePolicy(),
) -> tuple[AllocationObjectiveResult, ...]:
    materialized = tuple(inputs)
    ids = [item.request.opportunity_id for item in materialized]
    if len(ids) != len(set(ids)):
        raise ValueError("opportunity_id values must be unique within an objective batch")
    results = tuple(calculate_allocation_objective(item, policy) for item in materialized)
    return tuple(sorted(results, key=lambda item: item.deterministic_key))
