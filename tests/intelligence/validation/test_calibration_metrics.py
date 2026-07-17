from datetime import date
from decimal import Decimal

from foundation.intelligence.validation import (
    OutcomeRecord,
    PredictionOutcomePair,
    PredictionRecord,
    calculate_calibration_summary,
)


def pair(index: int, score: int, outcome_return: str) -> PredictionOutcomePair:
    prediction = PredictionRecord(
        asset_id=f"asset:{index}",
        asset_class="test",
        prediction_date=date(2026, 1, 1),
        model_id="test_model",
        model_version="1.0.0",
        final_score=Decimal(score),
        score_band="strong" if score >= 70 else "weak",
        confidence_score=Decimal("100"),
        coverage_ratio=Decimal("1"),
    )
    outcome = OutcomeRecord(
        asset_id=prediction.asset_id,
        prediction_date=prediction.prediction_date,
        horizon_days=30,
        outcome_date=date(2026, 1, 31),
        starting_price=Decimal("100"),
        ending_price=Decimal("110"),
        total_return=Decimal(outcome_return),
    )
    return PredictionOutcomePair(prediction, outcome)


def test_calibration_summary_builds_quintiles() -> None:
    pairs = tuple(
        pair(index, score, outcome)
        for index, (score, outcome) in enumerate(
            [
                (10, "-0.10"),
                (20, "-0.05"),
                (30, "0.00"),
                (40, "0.02"),
                (50, "0.03"),
                (60, "0.04"),
                (70, "0.05"),
                (80, "0.08"),
                (90, "0.10"),
                (100, "0.15"),
            ],
            start=1,
        )
    )
    summary = calculate_calibration_summary(pairs, quantile_count=5)
    assert set(summary.quantiles) == {"Q1", "Q2", "Q3", "Q4", "Q5"}
    assert summary.top_bottom_spread > 0
    assert summary.calibration_error is not None
