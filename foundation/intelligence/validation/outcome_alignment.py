"""Forward outcome construction and prediction alignment."""

from __future__ import annotations

from bisect import bisect_left
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from .historical_observation import HistoricalObservation
from .outcome_record import OutcomeRecord
from .point_in_time import group_observations_by_asset
from .prediction_record import PredictionRecord


def _find_on_or_after(
    series: tuple[HistoricalObservation, ...],
    target_date: date,
) -> HistoricalObservation | None:
    dates = [item.observation_date for item in series]
    index = bisect_left(dates, target_date)
    if index >= len(series):
        return None
    return series[index]


def calculate_total_return(
    starting_price: Decimal,
    ending_price: Decimal,
) -> Decimal:
    if starting_price <= Decimal("0"):
        raise ValueError("starting_price must be greater than zero.")
    return (ending_price / starting_price) - Decimal("1")


def calculate_maximum_drawdown(
    prices: Iterable[Decimal],
) -> Decimal | None:
    values = tuple(prices)
    if not values:
        return None
    peak = values[0]
    maximum_drawdown = Decimal("0")
    for price in values:
        if price > peak:
            peak = price
        if peak > Decimal("0"):
            drawdown = (price / peak) - Decimal("1")
            if drawdown < maximum_drawdown:
                maximum_drawdown = drawdown
    return maximum_drawdown


def build_outcome(
    prediction: PredictionRecord,
    horizon_days: int,
    observations: Iterable[HistoricalObservation],
    *,
    benchmark_return: Decimal | None = None,
    source: str = "walk_forward",
) -> OutcomeRecord | None:
    """Build one realized forward outcome for a prediction and horizon."""
    grouped = group_observations_by_asset(observations)
    series = grouped.get(prediction.asset_id)
    if not series:
        return None

    start = _find_on_or_after(series, prediction.prediction_date)
    target_date = prediction.prediction_date + timedelta(days=horizon_days)
    end = _find_on_or_after(series, target_date)
    if start is None or end is None or start.price is None or end.price is None:
        return None

    path_prices = [
        item.price
        for item in series
        if item.price is not None
        and start.observation_date <= item.observation_date <= end.observation_date
    ]
    total_return = calculate_total_return(start.price, end.price)
    maximum_drawdown = calculate_maximum_drawdown(path_prices)

    return OutcomeRecord(
        asset_id=prediction.asset_id,
        prediction_date=prediction.prediction_date,
        horizon_days=horizon_days,
        outcome_date=end.observation_date,
        starting_price=start.price,
        ending_price=end.price,
        total_return=total_return,
        benchmark_return=benchmark_return,
        maximum_drawdown=maximum_drawdown,
        source=source,
    )
