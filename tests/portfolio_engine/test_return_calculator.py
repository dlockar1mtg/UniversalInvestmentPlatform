from decimal import Decimal

from foundation.portfolio_engine.performance import calculate_period_return


def test_period_return_removes_external_cash_flow() -> None:
    result = calculate_period_return(
        beginning_value=Decimal("1000"),
        ending_value=Decimal("1150"),
        net_external_cash_flow=Decimal("100"),
    )
    assert result.return_value == Decimal("0.05")
