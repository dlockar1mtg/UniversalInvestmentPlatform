"""Immutable contracts for Phase 5.3 capital allocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Mapping


def _money(value: Decimal | float | int | str, name: str) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite():
        raise ValueError(f"{name} must be finite")
    return converted


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values)})


class CapitalPoolType(str, Enum):
    ONE_TIME = "ONE_TIME"
    RECURRING = "RECURRING"
    REBALANCING = "REBALANCING"


class AllocationConstraintType(str, Enum):
    CAPITAL_RESERVE = "CAPITAL_RESERVE"
    MINIMUM_PURCHASE = "MINIMUM_PURCHASE"
    MAXIMUM_POSITION = "MAXIMUM_POSITION"
    ASSET_CLASS_LIMIT = "ASSET_CLASS_LIMIT"
    GROUP_LIMIT = "GROUP_LIMIT"
    LIQUIDITY_LIMIT = "LIQUIDITY_LIMIT"


class AllocationStatus(str, Enum):
    ALLOCATED = "ALLOCATED"
    PARTIALLY_ALLOCATED = "PARTIALLY_ALLOCATED"
    DEFERRED = "DEFERRED"
    EXCLUDED = "EXCLUDED"


class AllocationReasonCode(str, Enum):
    TARGET_FUNDED = "TARGET_FUNDED"
    PARTIAL_CAPITAL_LIMIT = "PARTIAL_CAPITAL_LIMIT"
    CAPITAL_EXHAUSTED = "CAPITAL_EXHAUSTED"
    BELOW_MINIMUM_PURCHASE = "BELOW_MINIMUM_PURCHASE"
    MAXIMUM_POSITION_REACHED = "MAXIMUM_POSITION_REACHED"
    ASSET_CLASS_LIMIT_REACHED = "ASSET_CLASS_LIMIT_REACHED"
    GROUP_LIMIT_REACHED = "GROUP_LIMIT_REACHED"
    LIQUIDITY_LIMIT_REACHED = "LIQUIDITY_LIMIT_REACHED"
    NOT_SELECTED_FOR_ALLOCATION = "NOT_SELECTED_FOR_ALLOCATION"


@dataclass(frozen=True)
class CapitalPool:
    pool_id: str
    pool_type: CapitalPoolType
    gross_capital: Decimal | float | int | str
    required_reserve: Decimal | float | int | str = Decimal("0")
    currency: str = "USD"
    as_of: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.pool_id.strip():
            raise ValueError("pool_id must not be blank")
        gross = _money(self.gross_capital, "gross_capital")
        reserve = _money(self.required_reserve, "required_reserve")
        if gross < 0 or reserve < 0:
            raise ValueError("capital amounts must be non-negative")
        if reserve > gross:
            raise ValueError("required_reserve must not exceed gross_capital")
        if not self.currency.strip():
            raise ValueError("currency must not be blank")
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        object.__setattr__(self, "gross_capital", gross)
        object.__setattr__(self, "required_reserve", reserve)

    @property
    def deployable_capital(self) -> Decimal:
        return self.gross_capital - self.required_reserve


@dataclass(frozen=True)
class AllocationBounds:
    minimum_amount: Decimal | float | int | str
    target_amount: Decimal | float | int | str
    maximum_amount: Decimal | float | int | str

    def __post_init__(self) -> None:
        minimum = _money(self.minimum_amount, "minimum_amount")
        target = _money(self.target_amount, "target_amount")
        maximum = _money(self.maximum_amount, "maximum_amount")
        if minimum < 0 or minimum > target or target > maximum:
            raise ValueError("allocation bounds must satisfy 0 <= minimum <= target <= maximum")
        object.__setattr__(self, "minimum_amount", minimum)
        object.__setattr__(self, "target_amount", target)
        object.__setattr__(self, "maximum_amount", maximum)


@dataclass(frozen=True)
class AllocationRequest:
    request_id: str
    opportunity_id: str
    ranking_batch_id: str
    priority_score: Decimal | float | int | str
    priority_tier: str
    bounds: AllocationBounds
    asset_class: str
    group_key: str
    currency: str = "USD"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("request_id", "opportunity_id", "ranking_batch_id", "priority_tier", "asset_class", "group_key", "currency"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        score = _money(self.priority_score, "priority_score")
        if score < 0 or score > 100:
            raise ValueError("priority_score must be between 0 and 100")
        object.__setattr__(self, "priority_score", score)
        object.__setattr__(self, "metadata", _freeze(self.metadata))


@dataclass(frozen=True)
class AllocationConstraint:
    constraint_id: str
    constraint_type: AllocationConstraintType
    limit_amount: Decimal | float | int | str
    scope_key: str = "PORTFOLIO"
    hard_constraint: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.constraint_id.strip() or not self.scope_key.strip():
            raise ValueError("constraint_id and scope_key must not be blank")
        limit = _money(self.limit_amount, "limit_amount")
        if limit < 0:
            raise ValueError("limit_amount must be non-negative")
        object.__setattr__(self, "limit_amount", limit)
        object.__setattr__(self, "metadata", _freeze(self.metadata))


@dataclass(frozen=True)
class AllocationLine:
    request_id: str
    opportunity_id: str
    requested_amount: Decimal | float | int | str
    allocated_amount: Decimal | float | int | str
    status: AllocationStatus
    reason_codes: tuple[AllocationReasonCode, ...]
    binding_constraints: tuple[str, ...] = ()
    evidence: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id.strip() or not self.opportunity_id.strip():
            raise ValueError("request_id and opportunity_id must not be blank")
        requested = _money(self.requested_amount, "requested_amount")
        allocated = _money(self.allocated_amount, "allocated_amount")
        if requested < 0 or allocated < 0 or allocated > requested:
            raise ValueError("allocation must satisfy 0 <= allocated_amount <= requested_amount")
        if not self.reason_codes:
            raise ValueError("reason_codes must not be empty")
        object.__setattr__(self, "requested_amount", requested)
        object.__setattr__(self, "allocated_amount", allocated)
        object.__setattr__(self, "evidence", _freeze(self.evidence))

    @property
    def unmet_amount(self) -> Decimal:
        return self.requested_amount - self.allocated_amount


@dataclass(frozen=True)
class CapitalAllocationResult:
    allocation_batch_id: str
    ranking_batch_id: str
    pool_id: str
    gross_capital: Decimal | float | int | str
    reserved_capital: Decimal | float | int | str
    allocated_capital: Decimal | float | int | str
    residual_capital: Decimal | float | int | str
    lines: tuple[AllocationLine, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for name in ("allocation_batch_id", "ranking_batch_id", "pool_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        amounts = {
            name: _money(getattr(self, name), name)
            for name in ("gross_capital", "reserved_capital", "allocated_capital", "residual_capital")
        }
        if any(value < 0 for value in amounts.values()):
            raise ValueError("result capital amounts must be non-negative")
        if amounts["gross_capital"] != amounts["reserved_capital"] + amounts["allocated_capital"] + amounts["residual_capital"]:
            raise ValueError("capital conservation requires gross = reserved + allocated + residual")
        if amounts["allocated_capital"] != sum((line.allocated_amount for line in self.lines), Decimal("0")):
            raise ValueError("allocated_capital must equal the allocation-line total")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        for name, value in amounts.items():
            object.__setattr__(self, name, value)
