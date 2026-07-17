from datetime import date
from decimal import Decimal

from foundation.intelligence.validation import (
    OutcomeRecord,
    PredictionOutcomePair,
    PredictionRecord,
    calculate_classification_metrics,
)


def pair(score: str, outcome_return: str) -> PredictionOutcomePair:
    prediction = PredictionRecord(
        asset_id=f"asset:{score}:{outcome_return}",
        asset_class="test",
        prediction_date=date(2026, 1, 1),
        model_id="test_model",
        model_version="1.0.0",
        final_score=Decimal(score),
        score_band="test",
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


def test_classification_metrics_counts_confusion_matrix() -> None:
    metrics = calculate_classification_metrics(
        (
            pair("80", "0.10"),
            pair("80", "-0.10"),
            pair("60", "-0.10"),
            pair("60", "0.10"),
        )
    )
    assert metrics.true_positive == 1
    assert metrics.false_positive == 1
    assert metrics.true_negative == 1
    assert metrics.false_negative == 1
    assert metrics.hit_rate == Decimal("0.5")
