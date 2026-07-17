"""Maximum drawdown and recovery tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class ValuePoint:
    date_value: date
    value: Decimal


@dataclass(slots=True)
class DrawdownResult:
    maximum_drawdown: Decimal
    peak_date: date | None
    trough_date: date | None
    recovery_date: date | None
    recovery_days: int | None


def calculate_maximum_drawdown(points: list[ValuePoint]) -> DrawdownResult:
    if not points:
        return DrawdownResult(Decimal("0"), None, None, None, None)

    ordered = sorted(points, key=lambda item: item.date_value)
    peak_value = ordered[0].value
    peak_date = ordered[0].date_value
    max_drawdown = Decimal("0")
    max_peak_date = peak_date
    trough_date = peak_date

    for point in ordered:
        if point.value > peak_value:
            peak_value = point.value
            peak_date = point.date_value
        if peak_value > 0:
            drawdown = point.value / peak_value - Decimal("1")
            if drawdown < max_drawdown:
                max_drawdown = drawdown
                max_peak_date = peak_date
                trough_date = point.date_value

    recovery_date = None
    if max_drawdown < 0:
        peak_target = next(
            point.value for point in ordered if point.date_value == max_peak_date
        )
        for point in ordered:
            if point.date_value > trough_date and point.value >= peak_target:
                recovery_date = point.date_value
                break

    recovery_days = (
        None
        if recovery_date is None
        else (recovery_date - trough_date).days
    )

    return DrawdownResult(
        maximum_drawdown=max_drawdown,
        peak_date=max_peak_date,
        trough_date=trough_date,
        recovery_date=recovery_date,
        recovery_days=recovery_days,
    )
