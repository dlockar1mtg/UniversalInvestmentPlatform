from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from foundation.production.metals_native_ingestion import (
    ingest_collected_surfaces,
    load_benchmark_csv,
    load_vehicle_csv,
)
from foundation.production.metals_native_store import MetalsNativeStore


def _store() -> MetalsNativeStore:
    return MetalsNativeStore(sqlite3.connect(":memory:"))


def test_store_initializes_and_tracks_empty_summary():
    store = _store()
    store.initialize()
    summary = store.summary()
    assert summary.benchmark_observation_count == 0
    assert summary.vehicle_observation_count == 0


def test_loads_and_persists_collected_surfaces(tmp_path: Path):
    benchmark = tmp_path / "benchmark.csv"
    benchmark.write_text(
        "series_id,observation_date,value,source,unit\nGOLD,2026-07-25,2400.5,world-bank,usd_per_ounce\n",
        encoding="utf-8",
    )
    vehicle = tmp_path / "vehicle.csv"
    vehicle.write_text(
        "ticker,observation_date,close,adjusted_close,volume,source\nGLD,2026-07-25,225.5,225.4,1000000,alpha-vantage\n",
        encoding="utf-8",
    )
    store = _store()
    result = ingest_collected_surfaces(
        store,
        run_id="run-1",
        benchmark_paths=[benchmark],
        vehicle_paths=[vehicle],
    )
    assert result.status == "PASS"
    assert result.benchmark_rows == 1
    assert result.vehicle_rows == 1
    summary = store.summary()
    assert summary.latest_benchmark_date == "2026-07-25"
    assert summary.latest_vehicle_date == "2026-07-25"


def test_loads_uip_daily_market_schema(tmp_path: Path):
    vehicle = tmp_path / "daily_market_input.csv"
    vehicle.write_text(
        "ticker,trading_date,close_price,previous_close_price,benchmark_symbol,"
        "benchmark_close_price,benchmark_previous_close_price,expense_ratio_pct,"
        "average_daily_volume_shares,median_bid_ask_spread_pct,metadata_as_of_date\n"
        "BIL,2026-07-24,91.61,91.58,^IRX,3.805,3.80,0.1353,9901829,0.01,2026-07-25\n",
        encoding="utf-8",
    )

    rows = load_vehicle_csv(vehicle, run_id="uip-daily")

    assert len(rows) == 1
    assert rows[0].ticker == "BIL"
    assert rows[0].observation_date == "2026-07-24"
    assert rows[0].close == pytest.approx(91.61)
    assert rows[0].volume == pytest.approx(9901829.0)
    assert rows[0].source == "universal-market-provider"


def test_upsert_is_idempotent(tmp_path: Path):
    benchmark = tmp_path / "benchmark.csv"
    benchmark.write_text(
        "series_id,observation_date,value,source,unit\nGOLD,2026-07-25,2400.5,world-bank,usd_per_ounce\n",
        encoding="utf-8",
    )
    store = _store()
    store.initialize()
    rows = load_benchmark_csv(benchmark, run_id="one")
    assert store.upsert_benchmark_observations(rows) == 1
    rows = load_benchmark_csv(benchmark, run_id="two")
    assert store.upsert_benchmark_observations(rows) == 1
    assert store.summary().benchmark_observation_count == 1


def test_rejects_incomplete_benchmark_row(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("series_id,observation_date,value,source\nGOLD,2026-07-25,,world-bank\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_benchmark_csv(path, run_id="bad")


def test_rejects_incomplete_vehicle_row(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("ticker,observation_date,close\nGLD,2026-07-25,\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_vehicle_csv(path, run_id="bad")


def test_postgres_parameter_style_is_generated():
    connection = sqlite3.connect(":memory:")
    store = MetalsNativeStore(connection, parameter_style="format")
    assert store._sql("VALUES (?, ?)") == "VALUES (%s, %s)"


def test_invalid_parameter_style_is_rejected():
    with pytest.raises(ValueError):
        MetalsNativeStore(sqlite3.connect(":memory:"), parameter_style="named")
