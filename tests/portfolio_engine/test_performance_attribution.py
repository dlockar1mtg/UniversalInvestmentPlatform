from decimal import Decimal

from foundation.portfolio_engine.performance import (
    AttributionInput,
    calculate_attribution,
)


def test_attribution_uses_beginning_weights() -> None:
    results = calculate_attribution(
        [
            AttributionInput("crypto", Decimal("0.40"), Decimal("0.10")),
            AttributionInput("stocks", Decimal("0.60"), Decimal("0.05")),
        ]
    )
    assert results[0].contribution_to_return == Decimal("0.0400")
    assert results[1].contribution_to_return == Decimal("0.0300")
