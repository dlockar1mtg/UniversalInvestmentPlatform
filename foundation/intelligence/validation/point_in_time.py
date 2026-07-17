"""Point-in-time observation selection and anti-leakage checks."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable

from .historical_observation import HistoricalObservation


def assert_no_future_observations(
    observations: Iterable[HistoricalObservation],
    prediction_date: date,
) -> None:
    """Raise when an observation occurs after the prediction date."""
    future = [
        observation
        for observation in observations
        if observation.observation_date > prediction_date
    ]
    if future:
        latest = max(item.observation_date for item in future)
        raise ValueError(
            "Future-data leakage detected: "
            f"observation dated {latest.isoformat()} exceeds prediction date "
            f"{prediction_date.isoformat()}."
        )


def select_latest_observations(
    observations: Iterable[HistoricalObservation],
    prediction_date: date,
) -> dict[str, HistoricalObservation]:
    """Select the latest available observation per asset on or before a date."""
    eligible = [
        observation
        for observation in observations
        if observation.observation_date <= prediction_date
    ]
    selected: dict[str, HistoricalObservation] = {}
    for observation in eligible:
        current = selected.get(observation.asset_id)
        if current is None or observation.observation_date > current.observation_date:
            selected[observation.asset_id] = observation
    return selected


def group_observations_by_asset(
    observations: Iterable[HistoricalObservation],
) -> dict[str, tuple[HistoricalObservation, ...]]:
    """Group observations by asset and sort each series chronologically."""
    grouped: dict[str, list[HistoricalObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.asset_id].append(observation)
    return {
        asset_id: tuple(sorted(rows, key=lambda item: item.observation_date))
        for asset_id, rows in grouped.items()
    }
