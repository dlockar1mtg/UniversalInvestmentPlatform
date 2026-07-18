"""Deterministic opportunity sizing before capital optimization."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .contracts import AllocationBounds, AllocationRequest
from .supply import CapitalSupplyResult


def _decimal(value, name: str) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


def _score(value, name: str) -> Decimal:
    converted = _decimal(value, name)
    if converted > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return converted


class SizingStatus(str, Enum):
    SIZEABLE = "SIZEABLE"
    CONSTRAINED = "CONSTRAINED"
    UNSIZEABLE = "UNSIZEABLE"


class SizingReasonCode(str, Enum):
    CONVICTION_ADJUSTED = "CONVICTION_ADJUSTED"
    PURCHASE_MINIMUM_APPLIED = "PURCHASE_MINIMUM_APPLIED"
    PORTFOLIO_GAP_LIMIT = "PORTFOLIO_GAP_LIMIT"
    OPPORTUNITY_CAPACITY_LIMIT = "OPPORTUNITY_CAPACITY_LIMIT"
    LIQUIDITY_LIMIT = "LIQUIDITY_LIMIT"
    DEPLOYABLE_CAPITAL_LIMIT = "DEPLOYABLE_CAPITAL_LIMIT"
    BELOW_FEASIBLE_MINIMUM = "BELOW_FEASIBLE_MINIMUM"
    NO_PORTFOLIO_GAP = "NO_PORTFOLIO_GAP"


@dataclass(frozen=True)
class SizingInputs:
    request: AllocationRequest
    confidence_score: Decimal | float | int | str
    action_strength_score: Decimal | float | int | str
    portfolio_gap_amount: Decimal | float | int | str
    opportunity_capacity_amount: Decimal | float | int | str
    liquidity_capacity_amount: Decimal | float | int | str
    minimum_purchase_amount: Decimal | float | int | str = Decimal("0")

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence_score", _score(self.confidence_score, "confidence_score"))
        object.__setattr__(self, "action_strength_score", _score(self.action_strength_score, "action_strength_score"))
        for name in (
            "portfolio_gap_amount",
            "opportunity_capacity_amount",
            "liquidity_capacity_amount",
            "minimum_purchase_amount",
        ):
            object.__setattr__(self, name, _decimal(getattr(self, name), name))


@dataclass(frozen=True)
class SizingPolicy:
    priority_weight: Decimal | float | int | str = Decimal("0.50")
    confidence_weight: Decimal | float | int | str = Decimal("0.30")
    action_strength_weight: Decimal | float | int | str = Decimal("0.20")
    money_quantum: Decimal | float | int | str = Decimal("0.01")

    def __post_init__(self) -> None:
        priority = _decimal(self.priority_weight, "priority_weight")
        confidence = _decimal(self.confidence_weight, "confidence_weight")
        action = _decimal(self.action_strength_weight, "action_strength_weight")
        quantum = _decimal(self.money_quantum, "money_quantum")
        if priority + confidence + action != Decimal("1"):
            raise ValueError("sizing weights must sum to 1")
        if quantum == 0:
            raise ValueError("money_quantum must be positive")
        object.__setattr__(self, "priority_weight", priority)
        object.__setattr__(self, "confidence_weight", confidence)
        object.__setattr__(self, "action_strength_weight", action)
        object.__setattr__(self, "money_quantum", quantum)


@dataclass(frozen=True)
class OpportunitySizingResult:
    request_id: str
    opportunity_id: str
    original_bounds: AllocationBounds
    sized_bounds: AllocationBounds
    conviction_factor: Decimal
    status: SizingStatus
    reason_codes: tuple[SizingReasonCode, ...]
    binding_limits: tuple[str, ...]


def size_opportunity(
    inputs: SizingInputs,
    supply: CapitalSupplyResult,
    policy: SizingPolicy = SizingPolicy(),
) -> OpportunitySizingResult:
    """Calculate feasible bounds without consuming deployable capital."""
    request = inputs.request
    conviction = (
        request.priority_score * policy.priority_weight
        + inputs.confidence_score * policy.confidence_weight
        + inputs.action_strength_score * policy.action_strength_weight
    ) / Decimal("100")
    conviction = conviction.quantize(Decimal("0.0001"))

    if inputs.portfolio_gap_amount == 0:
        zero = AllocationBounds(0, 0, 0)
        return OpportunitySizingResult(
            request.request_id,
            request.opportunity_id,
            request.bounds,
            zero,
            conviction,
            SizingStatus.UNSIZEABLE,
            (SizingReasonCode.NO_PORTFOLIO_GAP,),
            ("portfolio_gap_amount",),
        )

    maximum_candidates = {
        "request_maximum": request.bounds.maximum_amount,
        "portfolio_gap_amount": inputs.portfolio_gap_amount,
        "opportunity_capacity_amount": inputs.opportunity_capacity_amount,
        "liquidity_capacity_amount": inputs.liquidity_capacity_amount,
        "deployable_capital": supply.deployable_capital,
    }
    feasible_maximum = min(maximum_candidates.values())
    minimum = max(request.bounds.minimum_amount, inputs.minimum_purchase_amount)
    binding = tuple(
        name for name, value in sorted(maximum_candidates.items()) if value == feasible_maximum
    )
    reasons: list[SizingReasonCode] = [SizingReasonCode.CONVICTION_ADJUSTED]
    reason_by_limit = {
        "portfolio_gap_amount": SizingReasonCode.PORTFOLIO_GAP_LIMIT,
        "opportunity_capacity_amount": SizingReasonCode.OPPORTUNITY_CAPACITY_LIMIT,
        "liquidity_capacity_amount": SizingReasonCode.LIQUIDITY_LIMIT,
        "deployable_capital": SizingReasonCode.DEPLOYABLE_CAPITAL_LIMIT,
    }
    for name in binding:
        if name in reason_by_limit:
            reasons.append(reason_by_limit[name])
    if inputs.minimum_purchase_amount > request.bounds.minimum_amount:
        reasons.append(SizingReasonCode.PURCHASE_MINIMUM_APPLIED)

    if feasible_maximum < minimum:
        zero = AllocationBounds(0, 0, 0)
        return OpportunitySizingResult(
            request.request_id,
            request.opportunity_id,
            request.bounds,
            zero,
            conviction,
            SizingStatus.UNSIZEABLE,
            tuple(dict.fromkeys((*reasons, SizingReasonCode.BELOW_FEASIBLE_MINIMUM))),
            binding,
        )

    target_ceiling = min(request.bounds.target_amount, feasible_maximum)
    target = minimum + (target_ceiling - minimum) * conviction
    target = target.quantize(policy.money_quantum)
    target = min(max(target, minimum), feasible_maximum)
    sized = AllocationBounds(minimum, target, feasible_maximum)
    constrained = (
        sized != request.bounds
        or inputs.minimum_purchase_amount > request.bounds.minimum_amount
    )
    return OpportunitySizingResult(
        request.request_id,
        request.opportunity_id,
        request.bounds,
        sized,
        conviction,
        SizingStatus.CONSTRAINED if constrained else SizingStatus.SIZEABLE,
        tuple(dict.fromkeys(reasons)),
        binding,
    )


def size_opportunities(
    inputs: Iterable[SizingInputs],
    supply: CapitalSupplyResult,
    policy: SizingPolicy = SizingPolicy(),
) -> tuple[OpportunitySizingResult, ...]:
    """Validate and size a batch in stable opportunity-id order."""
    materialized = tuple(inputs)
    ids = [item.request.opportunity_id for item in materialized]
    if len(ids) != len(set(ids)):
        raise ValueError("opportunity_id values must be unique within a sizing batch")
    return tuple(
        size_opportunity(item, supply, policy)
        for item in sorted(materialized, key=lambda value: value.request.opportunity_id)
    )
