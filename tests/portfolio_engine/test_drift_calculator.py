from decimal import Decimal

from foundation.portfolio_engine.allocation import AllocationStatus, calculate_drift


def test_drift_identifies_overweight_category() -> None:
    result = calculate_drift(
        actual_value=Decimal("38000"),
        total_value=Decimal("100000"),
        target_weight=Decimal("0.33"),
        minimum_weight=Decimal("0.28"),
        maximum_weight=Decimal("0.38"),
    )
    assert result.actual_weight == Decimal("0.38")
    assert result.percentage_point_drift == Decimal("0.05")
    assert result.dollar_variance == Decimal("5000.00")
    assert result.status == AllocationStatus.WITHIN_BAND
