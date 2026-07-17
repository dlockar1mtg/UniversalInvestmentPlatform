from datetime import date
from decimal import Decimal

from foundation.portfolio_engine.risk import ValuePoint, calculate_maximum_drawdown


def test_maximum_drawdown_and_recovery() -> None:
    result = calculate_maximum_drawdown(
        [
            ValuePoint(date(2026, 1, 1), Decimal("100")),
            ValuePoint(date(2026, 2, 1), Decimal("120")),
            ValuePoint(date(2026, 3, 1), Decimal("90")),
            ValuePoint(date(2026, 4, 1), Decimal("121")),
        ]
    )
    assert result.maximum_drawdown == Decimal("-0.25")
    assert result.recovery_date == date(2026, 4, 1)
