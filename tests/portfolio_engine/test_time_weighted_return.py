from decimal import Decimal

from foundation.portfolio_engine.performance import calculate_time_weighted_return


def test_time_weighted_return_compounds_subperiods() -> None:
    result = calculate_time_weighted_return(
        [Decimal("0.10"), Decimal("-0.05")]
    )
    assert result == Decimal("0.0450")
