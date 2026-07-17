from datetime import date, datetime
from decimal import Decimal

import pytest

from foundation.intelligence.validation import (
    BacktestConfiguration,
    HistoricalObservation,
    OutcomeRecord,
    PredictionRecord,
    RebalanceFrequency,
    ValidationProfile,
    ValidationResult,
)


def test_historical_observation_is_immutable() -> None:
    observation = HistoricalObservation(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        observation_date=date(2026, 1, 1),
        price=Decimal("50000"),
        features={"momentum": Decimal("0.2")},
        source="fixture",
        data_version="1.0.0",
    )
    assert observation.price == Decimal("50000")
    with pytest.raises(TypeError):
        observation.features["new"] = 1


def test_prediction_record_validates_ranges() -> None:
    prediction = PredictionRecord(
        asset_id="crypto:bitcoin",
        asset_class="crypto",
        prediction_date=date(2026, 1, 1),
        model_id="crypto_core_v1",
        model_version="1.0.0",
        final_score=Decimal("82"),
        score_band="very_strong",
        confidence_score=Decimal("90"),
        coverage_ratio=Decimal("0.95"),
    )
    assert prediction.final_score == Decimal("82")


def test_outcome_record_requires_forward_date() -> None:
    with pytest.raises(ValueError):
        OutcomeRecord(
            asset_id="crypto:bitcoin",
            prediction_date=date(2026, 1, 1),
            horizon_days=30,
            outcome_date=date(2026, 1, 1),
            starting_price=Decimal("100"),
            ending_price=Decimal("110"),
            total_return=Decimal("0.10"),
        )


def test_backtest_configuration_sorts_horizons() -> None:
    config = BacktestConfiguration(
        backtest_id="crypto_walk_forward_v1",
        model_id="crypto_core_v1",
        model_version="1.0.0",
        asset_class="crypto",
        start_date=date(2020, 1, 1),
        end_date=date(2026, 1, 1),
        horizons_days=(365, 30, 90),
        rebalance_frequency=RebalanceFrequency.MONTHLY,
    )
    assert config.horizons_days == (30, 90, 365)


def test_backtest_configuration_rejects_duplicate_horizons() -> None:
    with pytest.raises(ValueError):
        BacktestConfiguration(
            backtest_id="bad",
            model_id="crypto_core_v1",
            model_version="1.0.0",
            asset_class="crypto",
            start_date=date(2020, 1, 1),
            end_date=date(2026, 1, 1),
            horizons_days=(30, 30),
            rebalance_frequency=RebalanceFrequency.MONTHLY,
        )


def test_validation_profile_freezes_thresholds() -> None:
    profile = ValidationProfile(
        profile_id="baseline_v1",
        version="1.0.0",
        minimum_observations=100,
        minimum_assets=5,
        minimum_date_coverage=Decimal("0.8"),
        rank_metrics=("spearman",),
        performance_metrics=("hit_rate",),
        thresholds={"hit_rate": Decimal("0.5")},
    )
    with pytest.raises(TypeError):
        profile.thresholds["new"] = Decimal("1")


def test_validation_result_requires_metrics() -> None:
    with pytest.raises(ValueError):
        ValidationResult(
            validation_run_id="run-1",
            backtest_id="backtest-1",
            model_id="crypto_core_v1",
            model_version="1.0.0",
            horizon_days=30,
            observation_count=100,
            asset_count=5,
            metrics={},
            passed=True,
            generated_at=datetime(2026, 7, 17, 12, 0, 0),
        )
