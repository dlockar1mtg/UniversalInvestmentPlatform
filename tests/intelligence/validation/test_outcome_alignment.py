from datetime import date
from decimal import Decimal

from foundation.intelligence.validation import (
    HistoricalObservation,
    PredictionRecord,
    build_outcome,
    calculate_maximum_drawdown,
    calculate_total_return,
)


def observation(day: int, price: str) -> HistoricalObservation:
    return HistoricalObservation(
        asset_id="etf:VOO",
        asset_class="etf",
        observation_date=date(2026, 1, day),
        price=Decimal(price),
        features={},
        source="fixture",
        data_version="1.0.0",
    )


def prediction() -> PredictionRecord:
    return PredictionRecord(
        asset_id="etf:VOO",
        asset_class="etf",
        prediction_date=date(2026, 1, 1),
        model_id="etf_core_v1",
        model_version="1.0.0",
        final_score=Decimal("80"),
        score_band="very_strong",
        confidence_score=Decimal("90"),
        coverage_ratio=Decimal("1"),
    )


def test_total_return() -> None:
    assert calculate_total_return(Decimal("100"), Decimal("110")) == Decimal("0.1")


def test_maximum_drawdown() -> None:
    drawdown = calculate_maximum_drawdown(
        (Decimal("100"), Decimal("120"), Decimal("90"), Decimal("110"))
    )
    assert drawdown == Decimal("-0.25")


def test_build_outcome_uses_first_observation_on_or_after_target() -> None:
    outcome = build_outcome(
        prediction(),
        5,
        (
            observation(1, "100"),
            observation(4, "105"),
            observation(7, "110"),
        ),
    )
    assert outcome is not None
    assert outcome.outcome_date == date(2026, 1, 7)
    assert outcome.total_return == Decimal("0.1")
