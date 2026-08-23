"""Correction-aware portfolio accounting derived from the append-only TXN-1 ledger."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .transactions import InvestmentTransaction, TransactionType


ZERO = Decimal("0")


@dataclass(frozen=True)
class EffectiveTransactionSet:
    items: tuple[InvestmentTransaction, ...]
    superseded_transaction_ids: tuple[str, ...]


@dataclass
class _PositionState:
    domain_id: str
    asset_id: str
    account_id: str
    currency: str
    quantity: Decimal = ZERO
    known_quantity: Decimal = ZERO
    unknown_quantity: Decimal = ZERO
    known_cost_basis: Decimal = ZERO
    realized_pl_known: Decimal = ZERO
    realized_pl_complete: bool = True

    def basis_status(self) -> str:
        if self.quantity == ZERO:
            return "NONE"
        if self.known_quantity == self.quantity and self.unknown_quantity == ZERO:
            return "KNOWN"
        if self.known_quantity == ZERO and self.unknown_quantity == self.quantity:
            return "UNKNOWN"
        return "PARTIAL"


@dataclass(frozen=True)
class PortfolioPosition:
    domain_id: str
    asset_id: str
    account_id: str
    currency: str
    quantity: Decimal
    basis_status: str
    known_basis_quantity: Decimal
    unknown_basis_quantity: Decimal
    cost_basis: Decimal | None
    average_cost: Decimal | None
    realized_pl: Decimal | None

    def document(self) -> dict[str, object]:
        return {
            "domain_id": self.domain_id,
            "asset_id": self.asset_id,
            "account_id": self.account_id,
            "currency": self.currency,
            "quantity": str(self.quantity),
            "basis_status": self.basis_status,
            "known_basis_quantity": str(self.known_basis_quantity),
            "unknown_basis_quantity": str(self.unknown_basis_quantity),
            "cost_basis": None if self.cost_basis is None else str(self.cost_basis),
            "average_cost": None if self.average_cost is None else str(self.average_cost),
            "realized_pl": None if self.realized_pl is None else str(self.realized_pl),
        }


@dataclass(frozen=True)
class PortfolioAccountingResult:
    positions: tuple[PortfolioPosition, ...]
    effective_transaction_count: int
    superseded_transaction_count: int

    def document(self) -> dict[str, object]:
        known_basis = sum(
            (item.cost_basis for item in self.positions if item.cost_basis is not None),
            ZERO,
        )
        realized_known = sum(
            (item.realized_pl for item in self.positions if item.realized_pl is not None),
            ZERO,
        )
        return {
            "positions": [item.document() for item in self.positions],
            "position_count": len(self.positions),
            "effective_transaction_count": self.effective_transaction_count,
            "superseded_transaction_count": self.superseded_transaction_count,
            "known_cost_basis": str(known_basis),
            "realized_pl_known": str(realized_known),
            "pricing_status": "NOT_JOINED_YET",
        }


def resolve_effective_transactions(
    transactions: Iterable[InvestmentTransaction],
) -> EffectiveTransactionSet:
    """Resolve append-only correction chains to their effective leaf rows.

    A target may have at most one direct correction. Forks and cycles are rejected so
    portfolio ownership is never silently guessed.
    """

    items = tuple(transactions)
    by_id = {item.transaction_id: item for item in items}
    if len(by_id) != len(items):
        raise ValueError("duplicate transaction_id encountered in ledger")

    corrections: dict[str, InvestmentTransaction] = {}
    for item in items:
        target = item.corrects_transaction_id
        if target is None:
            continue
        if target not in by_id:
            raise ValueError("correction target is missing from supplied ledger window")
        if target in corrections:
            raise ValueError("correction fork detected; effective transaction is ambiguous")
        corrections[target] = item

    for start in by_id:
        seen: set[str] = set()
        current = start
        while current in corrections:
            if current in seen:
                raise ValueError("correction cycle detected")
            seen.add(current)
            current = corrections[current].transaction_id
        if current in seen:
            raise ValueError("correction cycle detected")

    superseded = tuple(sorted(corrections))
    leaves = tuple(
        sorted(
            (item for item in items if item.transaction_id not in corrections),
            key=lambda item: (item.occurred_at, item.recorded_at, item.transaction_id),
        )
    )
    return EffectiveTransactionSet(
        items=leaves,
        superseded_transaction_ids=superseded,
    )


def _key(item: InvestmentTransaction, account_id: str | None = None) -> tuple[str, str, str, str]:
    return (
        item.domain_id,
        item.asset_id,
        item.account_id if account_id is None else account_id,
        item.currency,
    )


def _state(
    states: dict[tuple[str, str, str, str], _PositionState],
    item: InvestmentTransaction,
    account_id: str | None = None,
) -> _PositionState:
    key = _key(item, account_id)
    if key not in states:
        states[key] = _PositionState(
            domain_id=key[0],
            asset_id=key[1],
            account_id=key[2],
            currency=key[3],
        )
    return states[key]


def _add_acquisition(state: _PositionState, item: InvestmentTransaction) -> None:
    state.quantity += item.quantity
    if item.price_per_unit is None:
        state.unknown_quantity += item.quantity
        return
    state.known_quantity += item.quantity
    state.known_cost_basis += item.quantity * item.price_per_unit + item.fees


def _require_quantity(state: _PositionState, quantity: Decimal) -> None:
    if state.quantity < quantity:
        raise ValueError(
            f"insufficient quantity for {state.domain_id}/{state.asset_id} in {state.account_id}"
        )


def _remove_quantity_and_basis(state: _PositionState, quantity: Decimal) -> Decimal | None:
    _require_quantity(state, quantity)
    status = state.basis_status()
    if status == "PARTIAL":
        raise ValueError(
            "cannot allocate SELL/TRANSFER against partial-basis position without governed lot policy"
        )
    if status == "KNOWN":
        average = state.known_cost_basis / state.known_quantity
        removed_basis = average * quantity
        state.quantity -= quantity
        state.known_quantity -= quantity
        state.known_cost_basis -= removed_basis
        if state.quantity == ZERO:
            state.known_quantity = ZERO
            state.known_cost_basis = ZERO
        return removed_basis
    if status == "UNKNOWN":
        state.quantity -= quantity
        state.unknown_quantity -= quantity
        if state.quantity == ZERO:
            state.unknown_quantity = ZERO
        return None
    raise ValueError("cannot remove quantity from an empty position")


def derive_portfolio(
    transactions: Iterable[InvestmentTransaction],
) -> PortfolioAccountingResult:
    effective = resolve_effective_transactions(transactions)
    states: dict[tuple[str, str, str, str], _PositionState] = {}

    for item in effective.items:
        source = _state(states, item)

        if item.transaction_type in {TransactionType.BUY, TransactionType.GIFT, TransactionType.ADJUSTMENT}:
            _add_acquisition(source, item)
            continue

        if item.transaction_type is TransactionType.SELL:
            removed_basis = _remove_quantity_and_basis(source, item.quantity)
            if removed_basis is None or item.price_per_unit is None:
                source.realized_pl_complete = False
            else:
                proceeds = item.quantity * item.price_per_unit - item.fees
                source.realized_pl_known += proceeds - removed_basis
            continue

        if item.transaction_type is TransactionType.TRANSFER:
            removed_basis = _remove_quantity_and_basis(source, item.quantity)
            destination = _state(states, item, item.destination_account_id)
            destination.quantity += item.quantity
            if removed_basis is None:
                destination.unknown_quantity += item.quantity
            else:
                destination.known_quantity += item.quantity
                destination.known_cost_basis += removed_basis
            continue

        raise ValueError(f"unsupported transaction type: {item.transaction_type}")

    positions: list[PortfolioPosition] = []
    for state in states.values():
        if state.quantity == ZERO:
            continue
        status = state.basis_status()
        cost_basis = state.known_cost_basis if status == "KNOWN" else None
        average_cost = (
            state.known_cost_basis / state.known_quantity
            if status == "KNOWN" and state.known_quantity > ZERO
            else None
        )
        positions.append(
            PortfolioPosition(
                domain_id=state.domain_id,
                asset_id=state.asset_id,
                account_id=state.account_id,
                currency=state.currency,
                quantity=state.quantity,
                basis_status=status,
                known_basis_quantity=state.known_quantity,
                unknown_basis_quantity=state.unknown_quantity,
                cost_basis=cost_basis,
                average_cost=average_cost,
                realized_pl=state.realized_pl_known if state.realized_pl_complete else None,
            )
        )

    positions.sort(key=lambda item: (item.domain_id, item.asset_id, item.account_id, item.currency))
    return PortfolioAccountingResult(
        positions=tuple(positions),
        effective_transaction_count=len(effective.items),
        superseded_transaction_count=len(effective.superseded_transaction_ids),
    )
