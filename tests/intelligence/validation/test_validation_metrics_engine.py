from datetime import date
from decimal import Decimal

from foundation.intelligence.validation import (
    BacktestDataset,
    BacktestDiagnostics,
    OutcomeRecord,
    PredictionOutcomePair,
    PredictionRecord,
    ValidationMetricsEngine,
)


def make_pair(index: int, horizon: int, score: int, outcome_return: str):
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
        horizon_days=horizon,
        outcome_date=date(2026, 2, 1),
        starting_price=Decimal("100"),
        ending_price=Decimal("110"),
        total_return=Decimal(outcome_return),
    )
    return PredictionOutcomePair(prediction, outcome)


def test_metrics_engine_calculates_all_horizons() -> None:
    pairs_30 = tuple(
        make_pair(i, 30, score, outcome)
        for i, (score, outcome) in enumerate(
            [(20, "-0.1"), (40, "0.0"), (60, "0.05"), (80, "0.1"), (100, "0.2")],
            start=1,
        )
    )
    pairs_90 = tuple(
        make_pair(i + 10, 90, score, outcome)
        for i, (score, outcome) in enumerate(
            [(20, "-0.05"), (40, "0.0"), (60, "0.02"), (80, "0.08"), (100, "0.15")],
            start=1,
        )
    )
    dataset = BacktestDataset(
        backtest_id="test_backtest",
        predictions=tuple(item.prediction for item in pairs_30 + pairs_90),
        outcomes=tuple(item.outcome for item in pairs_30 + pairs_90),
        pairs_by_horizon={30: pairs_30, 90: pairs_90},
        diagnostics=BacktestDiagnostics(
            prediction_dates_generated=1,
            predictions_generated=10,
            outcomes_generated=10,
            missing_observations=0,
            missing_outcomes=0,
            filtered_predictions=0,
        ),
    )
    report = ValidationMetricsEngine().calculate(dataset)
    assert set(report.horizons) == {30, 90}
    assert report.stability.mean_spearman is not None
    assert report.stability.positive_horizon_ratio == Decimal("1")
