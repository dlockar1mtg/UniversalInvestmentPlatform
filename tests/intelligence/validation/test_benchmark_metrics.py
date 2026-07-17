from datetime import date
from decimal import Decimal

from foundation.intelligence.validation import (
    OutcomeRecord,
    PredictionOutcomePair,
    PredictionRecord,
    calculate_alpha,
    calculate_benchmark_metrics,
    calculate_beta,
)


def pair(index: int, model_return: str, benchmark_return: str) -> PredictionOutcomePair:
    prediction = PredictionRecord(
        asset_id=f"asset:{index}",
        asset_class="test",
        prediction_date=date(2026, 1, 1),
        model_id="test_model",
        model_version="1.0.0",
        final_score=Decimal("80"),
        score_band="very_strong",
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
        total_return=Decimal(model_return),
        benchmark_return=Decimal(benchmark_return),
        maximum_drawdown=Decimal("-0.10"),
    )
    return PredictionOutcomePair(prediction, outcome)


def test_beta_and_alpha_for_identical_series() -> None:
    model = (Decimal("0.1"), Decimal("0.2"), Decimal("-0.1"))
    benchmark = model
    assert calculate_beta(model, benchmark) == Decimal("1")
    assert calculate_alpha(model, benchmark) == Decimal("0")


def test_benchmark_metrics() -> None:
    metrics = calculate_benchmark_metrics(
        (
            pair(1, "0.10", "0.05"),
            pair(2, "0.20", "0.10"),
            pair(3, "-0.05", "-0.10"),
        )
    )
    assert metrics.observation_count == 3
    assert metrics.mean_excess_return > 0
    assert metrics.benchmark_win_rate == Decimal("1")
    assert metrics.tracking_error is not None
    assert metrics.information_ratio is not None
