"""Prediction-date schedule generation for walk-forward validation."""

from __future__ import annotations

from datetime import date, timedelta

from .backtest_configuration import BacktestConfiguration, RebalanceFrequency


def _month_end(value: date) -> date:
    if value.month == 12:
        next_month = date(value.year + 1, 1, 1)
    else:
        next_month = date(value.year, value.month + 1, 1)
    return next_month - timedelta(days=1)


def _quarter_end(value: date) -> date:
    quarter = ((value.month - 1) // 3) + 1
    month = quarter * 3
    return _month_end(date(value.year, month, 1))


def _year_end(value: date) -> date:
    return date(value.year, 12, 31)


def generate_prediction_dates(
    configuration: BacktestConfiguration,
) -> tuple[date, ...]:
    """Generate deterministic prediction dates within the configured window."""
    start = configuration.start_date + timedelta(days=configuration.warmup_days)
    end = configuration.end_date
    if start > end:
        return ()

    frequency = configuration.rebalance_frequency
    dates: list[date] = []

    if frequency is RebalanceFrequency.DAILY:
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=1)

    elif frequency is RebalanceFrequency.WEEKLY:
        current = start
        while current <= end:
            dates.append(current)
            current += timedelta(days=7)

    elif frequency is RebalanceFrequency.MONTHLY:
        current = _month_end(start)
        if current < start:
            current = _month_end(date(start.year, start.month + 1, 1))
        while current <= end:
            dates.append(current)
            if current.month == 12:
                current = _month_end(date(current.year + 1, 1, 1))
            else:
                current = _month_end(date(current.year, current.month + 1, 1))

    elif frequency is RebalanceFrequency.QUARTERLY:
        current = _quarter_end(start)
        while current <= end:
            dates.append(current)
            month = current.month + 3
            year = current.year
            if month > 12:
                month -= 12
                year += 1
            current = _quarter_end(date(year, month, 1))

    elif frequency is RebalanceFrequency.ANNUALLY:
        current = _year_end(start)
        while current <= end:
            dates.append(current)
            current = date(current.year + 1, 12, 31)

    else:
        raise ValueError(f"Unsupported rebalance frequency: {frequency}.")

    return tuple(dates)
