from decimal import Decimal

from foundation.portfolio_engine.risk import annualized_volatility


def test_volatility_is_positive_for_variable_returns() -> None:
    result = annualized_volatility(
        [Decimal("0.01"), Decimal("0.03"), Decimal("-0.02")]
    )
    assert result > 0
