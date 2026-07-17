from datetime import date
from decimal import Decimal

from foundation.intelligence.validation import (
    BacktestDataset,
    BacktestDiagnostics,
    BenchmarkComparisonEngine,
    OutcomeRecord,
    PredictionOutcomePair,
    PredictionRecord,
)


def make_pair(index: int, horizon: int, model_return: str, benchmark_return: str):
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
        horizon_days=horizon,
        outcome_date=date(2026, 2, 1),
        starting_price=Decimal("100"),
        ending_price=Decimal("110"),
        total_return=Decimal(model_return),
        benchmark_return=Decimal(benchmark_return),
        maximum_drawdown=Decimal("-0.10"),
    )
    return PredictionOutcomePair(prediction, outcome)


def test_engine_calculates_all_horizons() -> None:
    pairs_30 = (
        make_pair(1, 30, "0.10", "0.05"),
        make_pair(2, 30, "0.20", "0.10"),
    )
    pairs_90 = (
        make_pair(3, 90, "0.15", "0.08"),
        make_pair(4, 90, "0.25", "0.12"),
    )
    dataset = BacktestDataset(
        backtest_id="benchmark_test",
        predictions=tuple(item.prediction for item in pairs_30 + pairs_90),
        outcomes=tuple(item.outcome for item in pairs_30 + pairs_90),
        pairs_by_horizon={30: pairs_30, 90: pairs_90},
        diagnostics=BacktestDiagnostics(
            prediction_dates_generated=1,
            predictions_generated=4,
            outcomes_generated=4,
            missing_observations=0,
            missing_outcomes=0,
            filtered_predictions=0,
        ),
    )
    report = BenchmarkComparisonEngine().calculate(dataset)
    assert set(report.by_horizon) == {30, 90}
    assert report.by_horizon[30].mean_excess_return > 0
