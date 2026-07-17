"""Aggregate portfolio risk summary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .downside_risk import downside_deviation
from .drawdown import ValuePoint, calculate_maximum_drawdown
from .risk_adjusted_returns import calmar_ratio, sharpe_ratio, sortino_ratio
from .volatility import annualized_volatility


@dataclass(slots=True)
class RiskSummary:
    annualized_volatility: Decimal
    downside_deviation: Decimal
    maximum_drawdown: Decimal
    drawdown_peak_date: date | None
    drawdown_trough_date: date | None
    recovery_date: date | None
    recovery_days: int | None
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    positive_period_percentage: Decimal
    best_period_return: Decimal
    worst_period_return: Decimal


def build_risk_summary(
    returns: list[Decimal],
    values: list[ValuePoint],
    *,
    annualized_return: Decimal,
    risk_free_rate: Decimal = Decimal("0"),
    periods_per_year: int = 12,
) -> RiskSummary:
    volatility = annualized_volatility(
        returns,
        periods_per_year=periods_per_year,
    )
    downside = downside_deviation(
        returns,
        periods_per_year=periods_per_year,
    )
    drawdown = calculate_maximum_drawdown(values)
    positive = (
        Decimal("0")
        if not returns
        else Decimal(sum(1 for value in returns if value > 0))
        / Decimal(len(returns))
    )

    return RiskSummary(
        annualized_volatility=volatility,
        downside_deviation=downside,
        maximum_drawdown=drawdown.maximum_drawdown,
        drawdown_peak_date=drawdown.peak_date,
        drawdown_trough_date=drawdown.trough_date,
        recovery_date=drawdown.recovery_date,
        recovery_days=drawdown.recovery_days,
        sharpe_ratio=sharpe_ratio(
            annualized_return,
            volatility,
            risk_free_rate=risk_free_rate,
        ),
        sortino_ratio=sortino_ratio(
            annualized_return,
            downside,
        ),
        calmar_ratio=calmar_ratio(
            annualized_return,
            drawdown.maximum_drawdown,
        ),
        positive_period_percentage=positive,
        best_period_return=max(returns) if returns else Decimal("0"),
        worst_period_return=min(returns) if returns else Decimal("0"),
    )
