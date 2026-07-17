from decimal import Decimal

from foundation.portfolio_engine.risk import calmar_ratio, sharpe_ratio, sortino_ratio


def test_risk_adjusted_metrics() -> None:
    assert sharpe_ratio(Decimal("0.12"), Decimal("0.10")) == Decimal("1.2")
    assert sortino_ratio(Decimal("0.12"), Decimal("0.08")) == Decimal("1.5")
    assert calmar_ratio(Decimal("0.12"), Decimal("-0.20")) == Decimal("0.6")
