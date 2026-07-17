"""Weighted-average cost basis calculations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class CostBasisState:
    quantity: Decimal = Decimal("0")
    cost_basis: Decimal = Decimal("0")
    realized_gain_loss: Decimal = Decimal("0")

    @property
    def average_unit_cost(self) -> Decimal:
        if self.quantity == 0:
            return Decimal("0")
        return self.cost_basis / self.quantity


def apply_buy(
    state: CostBasisState,
    *,
    quantity: Decimal,
    gross_amount: Decimal,
    fees: Decimal = Decimal("0"),
) -> CostBasisState:
    quantity = Decimal(str(quantity))
    gross_amount = Decimal(str(gross_amount))
    fees = Decimal(str(fees))
    if quantity <= 0:
        raise ValueError("Buy quantity must be positive.")
    if gross_amount < 0 or fees < 0:
        raise ValueError("Buy amount and fees cannot be negative.")

    return CostBasisState(
        quantity=state.quantity + quantity,
        cost_basis=state.cost_basis + gross_amount + fees,
        realized_gain_loss=state.realized_gain_loss,
    )


def apply_sell(
    state: CostBasisState,
    *,
    quantity: Decimal,
    gross_amount: Decimal,
    fees: Decimal = Decimal("0"),
) -> CostBasisState:
    quantity = Decimal(str(quantity))
    gross_amount = Decimal(str(gross_amount))
    fees = Decimal(str(fees))
    if quantity <= 0:
        raise ValueError("Sell quantity must be positive.")
    if quantity > state.quantity:
        raise ValueError("Cannot sell more than the current quantity.")
    if gross_amount < 0 or fees < 0:
        raise ValueError("Sell amount and fees cannot be negative.")

    average_cost = state.average_unit_cost
    removed_basis = average_cost * quantity
    proceeds = gross_amount - fees
    remaining_quantity = state.quantity - quantity
    remaining_basis = state.cost_basis - removed_basis
    if remaining_quantity == 0:
        remaining_basis = Decimal("0")

    return CostBasisState(
        quantity=remaining_quantity,
        cost_basis=remaining_basis,
        realized_gain_loss=state.realized_gain_loss + proceeds - removed_basis,
    )
