from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ingestion_rehearsal_is_isolated_and_fail_closed() -> None:
    source = (ROOT / "scripts/rehearse_metals_market_history_ingestion.py").read_text(encoding="utf-8")
    assert 'EXPECTED_CONTRACT_ID = "METALS-MARKET-HISTORY-1"' in source
    assert "tempfile.TemporaryDirectory" in source
    assert "MetalsNativeStore(connection, parameter_style=\"qmark\")" in source
    assert "metals_market_benchmark_observations" in source
    assert '"production_database_write_authorized": False' in source
    assert '"forecast_refresh_authorized": False' in source
    assert '"model_retraining_authorized": False' in source
    assert '"momentum_policy_authorized": False' in source
    assert '"tactical_posture_authorized": False' in source
    assert '"automatic_execution_authorized": False' in source
    assert '"next_decision": "AUTHORIZE_METALS_MARKET_HISTORY_PRODUCTION_SCHEMA_AND_INGESTION"' in source


def test_ingestion_rehearsal_requires_exact_registry_coverage_and_no_duplicates() -> None:
    source = (ROOT / "scripts/rehearse_metals_market_history_ingestion.py").read_text(encoding="utf-8")
    assert "enabled_tickers != expected_tickers" in source
    assert "len(vehicle_keys) != len(set(vehicle_keys))" in source
    assert "len(benchmark_keys) != len(set(benchmark_keys))" in source
    assert "vehicle_count != len(vehicle_rows)" in source
    assert "benchmark_count != len(benchmark_rows)" in source
    assert "set(latest_vehicle) != set(enabled_tickers)" in source
    assert "set(latest_benchmark) != set(expected_benchmarks)" in source
