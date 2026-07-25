from pathlib import Path

import pytest

from foundation.production.metals_outcome_tracking import (
    MetalsOutcomeObservation,
    evaluate_metals_outcomes,
    publish_metals_outcomes,
    summarize_by_regime,
    summarize_metals_outcomes,
)


def sample(**overrides):
    values = dict(
        forecast_id="f-1",
        asset_id="gold",
        vehicle_ticker="IAU",
        horizon_days=30,
        forecast_return_pct=5.0,
        forecast_probability_up=0.70,
        recommendation="BUY",
        signal_price=100.0,
        realized_price=104.0,
        benchmark_return_pct=3.0,
        regime="expansion",
        portfolio_weight_pct=10.0,
        estimated_slippage_pct=0.10,
    )
    values.update(overrides)
    return MetalsOutcomeObservation(**values)


def test_evaluates_forecast_and_recommendation():
    row = evaluate_metals_outcomes([sample()])[0]
    assert row.realized_return_pct == 4.0
    assert row.absolute_error_pct == 1.0
    assert row.directional_hit is True
    assert row.recommendation_hit is True
    assert row.net_return_after_slippage_pct == 3.9
    assert row.portfolio_contribution_pct == 0.39


def test_directional_miss_and_sell_hit():
    row = evaluate_metals_outcomes([sample(forecast_id="f-2", forecast_return_pct=2.0, recommendation="SELL", realized_price=95.0)])[0]
    assert row.directional_hit is False
    assert row.recommendation_hit is True


def test_duplicate_forecasts_fail_closed():
    with pytest.raises(ValueError, match="duplicate forecast_id"):
        evaluate_metals_outcomes([sample(), sample()])


def test_summary_and_regime_metrics():
    rows = evaluate_metals_outcomes([
        sample(),
        sample(forecast_id="f-2", asset_id="silver", vehicle_ticker="SLV", regime="contraction", realized_price=98.0, recommendation="SELL", forecast_return_pct=-1.0),
    ])
    summary = summarize_metals_outcomes(rows)
    regimes = summarize_by_regime(rows)
    assert summary["status"] == "PASS"
    assert summary["outcome_count"] == 2
    assert len(regimes) == 2


def test_outputs_are_written(tmp_path: Path):
    rows = evaluate_metals_outcomes([sample()])
    publish_metals_outcomes(rows, summarize_metals_outcomes(rows), tmp_path)
    assert (tmp_path / "metals_outcome_summary.json").exists()
    assert (tmp_path / "metals_outcomes.json").exists()
    assert (tmp_path / "metals_outcomes.csv").exists()
    assert (tmp_path / "metals_regime_performance.json").exists()
