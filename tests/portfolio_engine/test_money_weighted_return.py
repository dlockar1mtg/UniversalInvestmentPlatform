from datetime import date
from decimal import Decimal

from foundation.portfolio_engine.performance import (
    DatedCashFlow,
    calculate_money_weighted_return,
)


def test_money_weighted_return_approximates_ten_percent() -> None:
    result = calculate_money_weighted_return(
        [
            DatedCashFlow(date(2025, 1, 1), Decimal("-1000")),
            DatedCashFlow(date(2026, 1, 1), Decimal("1100")),
        ]
    )
    assert abs(result - Decimal("0.10")) < Decimal("0.000001")
