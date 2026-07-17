from decimal import Decimal

from foundation.portfolio_engine.positions import CostBasisState, apply_buy, apply_sell


def test_weighted_average_cost_basis_and_realized_gain() -> None:
    state = CostBasisState()
    state = apply_buy(state, quantity=Decimal("1"), gross_amount=Decimal("40000"))
    state = apply_buy(state, quantity=Decimal("1"), gross_amount=Decimal("60000"))
    assert state.quantity == Decimal("2")
    assert state.average_unit_cost == Decimal("50000")

    state = apply_sell(
        state,
        quantity=Decimal("0.5"),
        gross_amount=Decimal("30000"),
    )
    assert state.quantity == Decimal("1.5")
    assert state.cost_basis == Decimal("75000.0")
    assert state.realized_gain_loss == Decimal("5000.0")
