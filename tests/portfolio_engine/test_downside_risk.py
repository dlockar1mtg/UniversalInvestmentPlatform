from decimal import Decimal

from foundation.portfolio_engine.risk import downside_deviation


def test_downside_deviation_ignores_positive_returns() -> None:
    result = downside_deviation(
        [Decimal("0.10"), Decimal("-0.05"), Decimal("0.02")]
    )
    assert result > 0
