from decimal import Decimal

from foundation.portfolio_engine.rebalancing import projected_drift, projected_weight


def test_projected_weight_and_drift() -> None:
    weight = projected_weight(
        Decimal("20000"),
        Decimal("600"),
        Decimal("103000"),
    )
    drift = projected_drift(
        Decimal("20000"),
        Decimal("600"),
        Decimal("103000"),
        Decimal("0.20"),
    )
    assert weight == Decimal("20600") / Decimal("103000")
    assert drift == weight - Decimal("0.20")
