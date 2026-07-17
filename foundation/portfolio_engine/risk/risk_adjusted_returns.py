"""Risk-adjusted return metrics."""

from __future__ import annotations

from decimal import Decimal


def sharpe_ratio(
    annualized_return: Decimal,
    annualized_volatility: Decimal,
    *,
    risk_free_rate: Decimal = Decimal("0"),
) -> Decimal:
    volatility = Decimal(str(annualized_volatility))
    if volatility == 0:
        return Decimal("0")
    return (
        Decimal(str(annualized_return)) - Decimal(str(risk_free_rate))
    ) / volatility


def sortino_ratio(
    annualized_return: Decimal,
    downside_deviation: Decimal,
    *,
    minimum_acceptable_return: Decimal = Decimal("0"),
) -> Decimal:
    downside = Decimal(str(downside_deviation))
    if downside == 0:
        return Decimal("0")
    return (
        Decimal(str(annualized_return))
        - Decimal(str(minimum_acceptable_return))
    ) / downside


def calmar_ratio(
    annualized_return: Decimal,
    maximum_drawdown: Decimal,
) -> Decimal:
    drawdown = abs(Decimal(str(maximum_drawdown)))
    if drawdown == 0:
        return Decimal("0")
    return Decimal(str(annualized_return)) / drawdown
