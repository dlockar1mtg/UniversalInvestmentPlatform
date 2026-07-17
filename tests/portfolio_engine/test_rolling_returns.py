from datetime import date
from decimal import Decimal

from foundation.portfolio_engine.performance import (
    ReturnPoint,
    calculate_rolling_returns,
)


def test_rolling_two_period_return() -> None:
    points = [
        ReturnPoint(date(2026, 1, 31), Decimal("0.10")),
        ReturnPoint(date(2026, 2, 28), Decimal("0.05")),
        ReturnPoint(date(2026, 3, 31), Decimal("-0.02")),
    ]
    results = calculate_rolling_returns(points, window=2)
    assert len(results) == 2
    assert results[0].return_value == Decimal("0.1550")
