from datetime import date
from decimal import Decimal

from foundation.intelligence.validation import OutcomeRecord, PredictionRecord


def test_prediction_and_outcome_share_alignment_keys() -> None:
    prediction = PredictionRecord(
        asset_id="etf:VOO",
        asset_class="etf",
        prediction_date=date(2025, 1, 2),
        model_id="etf_core_v1",
        model_version="1.0.0",
        final_score=Decimal("75"),
        score_band="strong",
        confidence_score=Decimal("88"),
        coverage_ratio=Decimal("0.92"),
    )
    outcome = OutcomeRecord(
        asset_id="etf:VOO",
        prediction_date=date(2025, 1, 2),
        horizon_days=365,
        outcome_date=date(2026, 1, 2),
        starting_price=Decimal("500"),
        ending_price=Decimal("550"),
        total_return=Decimal("0.10"),
        benchmark_return=Decimal("0.08"),
        maximum_drawdown=Decimal("-0.12"),
    )
    assert prediction.asset_id == outcome.asset_id
    assert prediction.prediction_date == outcome.prediction_date
