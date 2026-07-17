from decimal import Decimal

from foundation.portfolio_engine.allocation import calculate_concentration


def test_concentration_metrics() -> None:
    result = calculate_concentration(
        [Decimal("0.40"), Decimal("0.30"), Decimal("0.20"), Decimal("0.10")]
    )
    assert result.largest_weight == Decimal("0.40")
    assert result.top_three_weight == Decimal("0.90")
    assert result.herfindahl_index == Decimal("0.30")
