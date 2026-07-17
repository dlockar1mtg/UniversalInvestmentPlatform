from decimal import Decimal

from foundation.portfolio_engine.rebalancing import apply_purchase_constraints


def test_fractional_purchase_uses_full_amount() -> None:
    result = apply_purchase_constraints(
        Decimal("143.72"),
        minimum_purchase_amount=Decimal("1"),
        allow_fractional=True,
    )
    assert result.executable_amount == Decimal("143.72")
    assert result.retained_amount == 0


def test_discrete_purchase_rounds_down_to_increment() -> None:
    result = apply_purchase_constraints(
        Decimal("620"),
        minimum_purchase_amount=Decimal("100"),
        allow_fractional=False,
        purchase_increment=Decimal("300"),
    )
    assert result.executable_amount == Decimal("600")
    assert result.retained_amount == Decimal("20")
