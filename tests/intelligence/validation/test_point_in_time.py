from datetime import date
from decimal import Decimal

import pytest

from foundation.intelligence.validation import (
    HistoricalObservation,
    assert_no_future_observations,
    select_latest_observations,
)


def observation(asset_id: str, day: int) -> HistoricalObservation:
    return HistoricalObservation(
        asset_id=asset_id,
        asset_class="crypto",
        observation_date=date(2026, 1, day),
        price=Decimal(str(100 + day)),
        features={},
        source="fixture",
        data_version="1.0.0",
    )


def test_select_latest_observation_per_asset() -> None:
    selected = select_latest_observations(
        (
            observation("a", 1),
            observation("a", 5),
            observation("a", 10),
            observation("b", 3),
        ),
        date(2026, 1, 6),
    )
    assert selected["a"].observation_date == date(2026, 1, 5)
    assert selected["b"].observation_date == date(2026, 1, 3)


def test_future_observation_detection() -> None:
    with pytest.raises(ValueError):
        assert_no_future_observations(
            (observation("a", 10),),
            date(2026, 1, 5),
        )
