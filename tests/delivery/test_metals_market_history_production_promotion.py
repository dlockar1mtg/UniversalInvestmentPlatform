from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_native_store_declares_market_benchmark_history_surface() -> None:
    source = (ROOT / "foundation/production/metals_native_store.py").read_text(encoding="utf-8")
    assert "class MetalsMarketBenchmarkObservation" in source
    assert "CREATE TABLE IF NOT EXISTS metals_market_benchmark_observations" in source
    assert "PRIMARY KEY (benchmark_symbol, observation_date, source)" in source
    assert "def upsert_market_benchmark_observations" in source


def test_production_promotion_is_transactional_and_fail_closed() -> None:
    source = (ROOT / "scripts/promote_metals_market_history_production.py").read_text(encoding="utf-8")
    assert 'EXPECTED_CONTRACT_ID = "METALS-MARKET-HISTORY-1"' in source
    assert "EXPECTED_VEHICLE_ROWS = 8283" in source
    assert "EXPECTED_BENCHMARK_ROWS = 4522" in source
    assert 'SOURCE = "yfinance"' in source
    assert 'RUN_ID = "metals-market-history-backfill-20260824"' in source
    assert "with psycopg.connect(dsn) as connection:" in source
    assert "ON CONFLICT (ticker, observation_date, source) DO UPDATE SET" in source
    assert "ON CONFLICT (benchmark_symbol, observation_date, source) DO UPDATE SET" in source
    assert '"production_database_write_executed": True' in source
    assert '"forecast_refresh_executed": False' in source
    assert '"model_retraining_executed": False' in source
    assert '"momentum_policy_authorized": False' in source
    assert '"tactical_posture_authorized": False' in source
    assert '"automatic_execution_authorized": False' in source
    assert '"next_decision": "VERIFY_METALS_MARKET_HISTORY_PRODUCTION_AUTHORITY"' in source
