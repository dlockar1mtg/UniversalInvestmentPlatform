from datetime import date
from decimal import Decimal

from foundation.intelligence.validation import (
    BacktestConfiguration,
    HistoricalObservation,
    PredictionRecord,
    RebalanceFrequency,
    WalkForwardBacktestEngine,
    WalkForwardRequest,
)


def observation(asset_id: str, value_date: date, price: str) -> HistoricalObservation:
    return HistoricalObservation(
        asset_id=asset_id,
        asset_class="crypto",
        observation_date=value_date,
        price=Decimal(price),
        features={"signal": Decimal("1")},
        source="fixture",
        data_version="1.0.0",
    )


def prediction_function(observation, prediction_date, config):
    return PredictionRecord(
        asset_id=observation.asset_id,
        asset_class=observation.asset_class,
        prediction_date=prediction_date,
        model_id=config.model_id,
        model_version=config.model_version,
        final_score=Decimal("80"),
        score_band="very_strong",
        confidence_score=Decimal("90"),
        coverage_ratio=Decimal("1"),
    )


def build_request():
    config = BacktestConfiguration(
        backtest_id="crypto_test",
        model_id="crypto_core_v1",
        model_version="1.0.0",
        asset_class="crypto",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        horizons_days=(7,),
        rebalance_frequency=RebalanceFrequency.WEEKLY,
    )
    observations = (
        observation("crypto:bitcoin", date(2026, 1, 1), "100"),
        observation("crypto:bitcoin", date(2026, 1, 8), "110"),
        observation("crypto:bitcoin", date(2026, 1, 15), "120"),
        observation("crypto:bitcoin", date(2026, 1, 22), "130"),
        observation("crypto:bitcoin", date(2026, 1, 29), "140"),
    )
    return WalkForwardRequest(config, observations)


def test_walk_forward_engine_generates_pairs() -> None:
    dataset = WalkForwardBacktestEngine().run(
        build_request(),
        prediction_function,
    )
    assert dataset.diagnostics.prediction_dates_generated == 5
    assert dataset.diagnostics.predictions_generated == 5
    assert len(dataset.pairs_by_horizon[7]) == 4
    assert dataset.diagnostics.missing_outcomes == 1


def test_walk_forward_engine_is_deterministic() -> None:
    engine = WalkForwardBacktestEngine()
    first = engine.run(build_request(), prediction_function)
    second = engine.run(build_request(), prediction_function)
    assert first == second


def test_walk_forward_engine_applies_score_filter() -> None:
    request = build_request()
    config = BacktestConfiguration(
        backtest_id=request.configuration.backtest_id,
        model_id=request.configuration.model_id,
        model_version=request.configuration.model_version,
        asset_class=request.configuration.asset_class,
        start_date=request.configuration.start_date,
        end_date=request.configuration.end_date,
        horizons_days=request.configuration.horizons_days,
        rebalance_frequency=request.configuration.rebalance_frequency,
        minimum_score=Decimal("90"),
    )
    dataset = WalkForwardBacktestEngine().run(
        WalkForwardRequest(config, request.observations),
        prediction_function,
    )
    assert dataset.diagnostics.predictions_generated == 0
    assert dataset.diagnostics.filtered_predictions == 5
