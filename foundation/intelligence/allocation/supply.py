"""Capital supply and reserve calculation for Phase 5.3."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping

from .contracts import CapitalPool


def _decimal(value: Decimal | float | int | str, name: str) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


class ReserveType(str, Enum):
    CONTRACTUAL = "CONTRACTUAL"
    REQUIRED = "REQUIRED"
    STRATEGIC_DRY_POWDER = "STRATEGIC_DRY_POWDER"


class CapitalSupplyStatus(str, Enum):
    FULLY_DEPLOYABLE = "FULLY_DEPLOYABLE"
    PARTIALLY_RESERVED = "PARTIALLY_RESERVED"
    FULLY_RESERVED = "FULLY_RESERVED"


@dataclass(frozen=True)
class ReserveRule:
    reserve_id: str
    reserve_type: ReserveType
    fixed_amount: Decimal | float | int | str = Decimal("0")
    gross_rate: Decimal | float | int | str = Decimal("0")
    minimum_amount: Decimal | float | int | str = Decimal("0")
    maximum_amount: Decimal | float | int | str | None = None
    evidence: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.reserve_id.strip():
            raise ValueError("reserve_id must not be blank")
        fixed = _decimal(self.fixed_amount, "fixed_amount")
        rate = _decimal(self.gross_rate, "gross_rate")
        minimum = _decimal(self.minimum_amount, "minimum_amount")
        maximum = None if self.maximum_amount is None else _decimal(
            self.maximum_amount, "maximum_amount"
        )
        if rate > 1:
            raise ValueError("gross_rate must be between 0 and 1")
        if maximum is not None and maximum < minimum:
            raise ValueError("maximum_amount must not be below minimum_amount")
        object.__setattr__(self, "fixed_amount", fixed)
        object.__setattr__(self, "gross_rate", rate)
        object.__setattr__(self, "minimum_amount", minimum)
        object.__setattr__(self, "maximum_amount", maximum)
        object.__setattr__(
            self,
            "evidence",
            MappingProxyType({str(key): self.evidence[key] for key in sorted(self.evidence)}),
        )

    def requested_amount(self, gross_capital: Decimal) -> Decimal:
        amount = max(self.minimum_amount, self.fixed_amount + gross_capital * self.gross_rate)
        if self.maximum_amount is not None:
            amount = min(amount, self.maximum_amount)
        return amount


@dataclass(frozen=True)
class ReserveLine:
    reserve_id: str
    reserve_type: ReserveType
    requested_amount: Decimal
    applied_amount: Decimal
    capped_by_available_capital: bool
    evidence: Mapping[str, object] = field(default_factory=dict)

    @property
    def unmet_reserve_amount(self) -> Decimal:
        return self.requested_amount - self.applied_amount


@dataclass(frozen=True)
class CapitalSupplyResult:
    pool_id: str
    currency: str
    gross_capital: Decimal
    unavailable_capital: Decimal
    reserved_capital: Decimal
    deployable_capital: Decimal
    status: CapitalSupplyStatus
    reserve_lines: tuple[ReserveLine, ...]

    def __post_init__(self) -> None:
        if self.gross_capital != (
            self.unavailable_capital + self.reserved_capital + self.deployable_capital
        ):
            raise ValueError(
                "capital conservation requires gross = unavailable + reserved + deployable"
            )
        if any(
            value < 0
            for value in (
                self.gross_capital,
                self.unavailable_capital,
                self.reserved_capital,
                self.deployable_capital,
            )
        ):
            raise ValueError("capital supply amounts must be non-negative")
        if self.reserved_capital != sum(
            (line.applied_amount for line in self.reserve_lines), Decimal("0")
        ):
            raise ValueError("reserved_capital must equal the reserve-line total")


_RESERVE_ORDER = {
    ReserveType.CONTRACTUAL: 0,
    ReserveType.REQUIRED: 1,
    ReserveType.STRATEGIC_DRY_POWDER: 2,
}


def calculate_capital_supply(
    pool: CapitalPool,
    reserve_rules: Iterable[ReserveRule] = (),
    *,
    unavailable_capital: Decimal | float | int | str = Decimal("0"),
) -> CapitalSupplyResult:
    """Calculate deployable capital with deterministic reserve precedence."""
    unavailable = _decimal(unavailable_capital, "unavailable_capital")
    if unavailable > pool.gross_capital:
        raise ValueError("unavailable_capital must not exceed gross_capital")
    rules = tuple(reserve_rules)
    identifiers = [rule.reserve_id for rule in rules]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("reserve_id values must be unique")

    ordered_rules = sorted(
        rules, key=lambda rule: (_RESERVE_ORDER[rule.reserve_type], rule.reserve_id)
    )
    available_for_reserves = pool.gross_capital - unavailable
    lines: list[ReserveLine] = []

    def apply(reserve_id: str, reserve_type: ReserveType, requested: Decimal, evidence):
        nonlocal available_for_reserves
        applied = min(requested, available_for_reserves)
        available_for_reserves -= applied
        lines.append(
            ReserveLine(
                reserve_id,
                reserve_type,
                requested,
                applied,
                applied < requested,
                MappingProxyType(dict(evidence)),
            )
        )

    if pool.required_reserve > 0:
        apply(
            "CONTRACTUAL_POOL_RESERVE",
            ReserveType.CONTRACTUAL,
            pool.required_reserve,
            {"source": "CapitalPool.required_reserve"},
        )
    for rule in ordered_rules:
        apply(
            rule.reserve_id,
            rule.reserve_type,
            rule.requested_amount(pool.gross_capital),
            rule.evidence,
        )

    reserved = sum((line.applied_amount for line in lines), Decimal("0"))
    deployable = pool.gross_capital - unavailable - reserved
    if deployable == pool.gross_capital:
        status = CapitalSupplyStatus.FULLY_DEPLOYABLE
    elif deployable == 0:
        status = CapitalSupplyStatus.FULLY_RESERVED
    else:
        status = CapitalSupplyStatus.PARTIALLY_RESERVED
    return CapitalSupplyResult(
        pool.pool_id,
        pool.currency,
        pool.gross_capital,
        unavailable,
        reserved,
        deployable,
        status,
        tuple(lines),
    )
