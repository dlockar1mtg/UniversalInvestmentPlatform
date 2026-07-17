"""Rolling compounded return windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class ReturnPoint:
    date_value: date
    return_value: Decimal


@dataclass(slots=True)
class RollingReturn:
    start_date: date
    end_date: date
    periods: int
    return_value: Decimal


def calculate_rolling_returns(
    points: list[ReturnPoint],
    *,
    window: int,
) -> list[RollingReturn]:
    if window <= 0:
        raise ValueError("Window must be positive.")
    ordered = sorted(points, key=lambda item: item.date_value)
    results: list[RollingReturn] = []

    for end_index in range(window - 1, len(ordered)):
        window_points = ordered[end_index - window + 1 : end_index + 1]
        growth = Decimal("1")
        for point in window_points:
            growth *= Decimal("1") + point.return_value
        results.append(
            RollingReturn(
                start_date=window_points[0].date_value,
                end_date=window_points[-1].date_value,
                periods=window,
                return_value=growth - Decimal("1"),
            )
        )

    return results
