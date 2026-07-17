from decimal import Decimal

from foundation.portfolio_engine.performance import compare_to_benchmark


def test_benchmark_comparison_calculates_excess_return() -> None:
    result = compare_to_benchmark(
        [Decimal("0.02"), Decimal("0.03")],
        [Decimal("0.01"), Decimal("0.02")],
    )
    assert result.portfolio_return > result.benchmark_return
    assert result.excess_return > 0
