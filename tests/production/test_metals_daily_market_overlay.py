from __future__ import annotations

from datetime import date
from pathlib import Path

from foundation.production.metals_daily_market_overlay import (
    DailyMarketObservation,
    build_daily_market_overlay,
    summarize_daily_market_overlay,
    write_daily_market_overlay_outputs,
)


def _observation(**overrides) -> DailyMarketObservation:
    values = {
        "ticker": "GLD",
        "trading_date": "2026-07-25",
        "close_price": 202.0,
        "previous_close_price": 200.0,
        "benchmark_symbol": "GOLD",
        "benchmark_close_price": 101.0,
        "benchmark_previous_close_price": 100.0,
        "expense_ratio_pct": 0.40,
        "average_daily_volume_shares": 6_000_000,
        "median_bid_ask_spread_pct": 0.05,
        "metadata_as_of_date": "2026-07-25",
    }
    values.update(overrides)
    return DailyMarketObservation(**values)


def test_current_normal_overlay_passes() -> None:
    rows = build_daily_market_overlay([_observation()], as_of=date(2026, 7, 25))
    assert len(rows) == 1
    assert rows[0].daily_return_pct == 1.0
    assert rows[0].benchmark_daily_return_pct == 1.0
    assert rows[0].divergence_status == "NORMAL"
    assert rows[0].alert_severity == "INFO"
    assert rows[0].freshness_status == "CURRENT"
    assert summarize_daily_market_overlay(rows)["status"] == "PASS"


def test_extreme_divergence_fails() -> None:
    rows = build_daily_market_overlay(
        [_observation(close_price=210.0, benchmark_close_price=101.0)],
        as_of=date(2026, 7, 25),
    )
    assert rows[0].divergence_status == "EXTREME"
    assert rows[0].alert_severity == "CRITICAL"
    assert summarize_daily_market_overlay(rows)["status"] == "FAIL"


def test_stale_market_evidence_fails_closed() -> None:
    rows = build_daily_market_overlay(
        [_observation(trading_date="2026-07-01")],
        as_of=date(2026, 7, 25),
    )
    assert rows[0].freshness_status == "STALE"
    assert rows[0].alert_severity == "CRITICAL"


def test_execution_quality_rewards_volume_and_tight_spread() -> None:
    rows = build_daily_market_overlay(
        [
            _observation(ticker="GLD"),
            _observation(
                ticker="SGOL",
                average_daily_volume_shares=100_000,
                median_bid_ask_spread_pct=0.8,
            ),
        ],
        as_of=date(2026, 7, 25),
    )
    by_ticker = {row.ticker: row for row in rows}
    assert by_ticker["GLD"].execution_quality_score > by_ticker["SGOL"].execution_quality_score


def test_outputs_are_written(tmp_path: Path) -> None:
    rows = build_daily_market_overlay([_observation()], as_of=date(2026, 7, 25))
    summary = summarize_daily_market_overlay(rows)
    write_daily_market_overlay_outputs(rows, summary, tmp_path)
    assert (tmp_path / "current_overlay.json").exists()
    assert (tmp_path / "current_overlay.csv").exists()
    assert (tmp_path / "overlay_summary.json").exists()
