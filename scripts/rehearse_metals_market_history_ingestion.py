from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_native_store import MetalsNativeStore, MetalsVehicleObservation
from foundation.production.metals_registry import load_metals_registry
from scripts.collect_metals_daily_market_input import BENCHMARKS

EXPECTED_CONTRACT_ID = "METALS-MARKET-HISTORY-1"
EXPECTED_VEHICLES = 11
EXPECTED_BENCHMARKS = 6
MIN_ROWS = 500


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"Required rehearsal evidence is missing: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _required(row: dict[str, str], *names: str) -> None:
    missing = [name for name in names if str(row.get(name, "")).strip() == ""]
    if missing:
        raise RuntimeError(f"History row is missing required fields {missing}: {row}")


def _optional_float(value: str) -> float | None:
    text = str(value or "").strip()
    return None if not text else float(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rehearse Metals three-year market-history ingestion in an isolated SQLite database.")
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()

    root = args.evidence_root.resolve()
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        raise RuntimeError(f"Backfill summary is missing: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS" or summary.get("contract_id") != EXPECTED_CONTRACT_ID:
        raise RuntimeError("Backfill evidence is not a certified METALS-MARKET-HISTORY-1 rehearsal.")
    if summary.get("rehearsal_only") is not True:
        raise RuntimeError("Backfill evidence is not marked rehearsal-only.")

    vehicle_rows = _read_csv(root / "vehicle_history.csv")
    benchmark_rows = _read_csv(root / "benchmark_market_history.csv")
    if len(vehicle_rows) != int(summary.get("vehicle_row_count") or -1):
        raise RuntimeError("Vehicle history row count does not match summary evidence.")
    if len(benchmark_rows) != int(summary.get("benchmark_row_count") or -1):
        raise RuntimeError("Benchmark history row count does not match summary evidence.")

    registry = load_metals_registry()
    enabled_tickers = tuple(sorted(vehicle.ticker for vehicle in registry.vehicles if vehicle.enabled))
    expected_tickers = tuple(sorted(BENCHMARKS))
    if enabled_tickers != expected_tickers or len(enabled_tickers) != EXPECTED_VEHICLES:
        raise RuntimeError("Enabled Metals vehicle registry does not match governed market-history coverage.")
    expected_benchmarks = tuple(sorted(set(BENCHMARKS.values())))
    if len(expected_benchmarks) != EXPECTED_BENCHMARKS:
        raise RuntimeError("Governed benchmark map does not contain six unique market benchmarks.")

    vehicle_keys: list[tuple[str, str, str]] = []
    vehicle_counts: Counter[str] = Counter()
    vehicle_objects: list[MetalsVehicleObservation] = []
    for row in vehicle_rows:
        _required(row, "ticker", "observation_date", "close", "source")
        ticker = row["ticker"].strip().upper()
        if ticker not in enabled_tickers:
            raise RuntimeError(f"Unknown or disabled vehicle in history evidence: {ticker}")
        source = row["source"].strip()
        key = (ticker, row["observation_date"].strip(), source)
        vehicle_keys.append(key)
        vehicle_counts[ticker] += 1
        vehicle_objects.append(
            MetalsVehicleObservation(
                ticker=ticker,
                observation_date=row["observation_date"].strip(),
                close=float(row["close"]),
                adjusted_close=_optional_float(row.get("adjusted_close", "")),
                volume=_optional_float(row.get("volume", "")),
                source=source,
                collected_at_utc="2026-08-24T00:00:00+00:00",
                run_id="metals-market-history-ingestion-rehearsal",
            )
        )
    if len(vehicle_keys) != len(set(vehicle_keys)):
        raise RuntimeError("Vehicle history contains duplicate primary keys.")
    if set(vehicle_counts) != set(enabled_tickers):
        raise RuntimeError("Vehicle history does not cover exactly the enabled Metals vehicles.")
    if any(count < MIN_ROWS for count in vehicle_counts.values()):
        raise RuntimeError("Vehicle history is below the governed minimum row depth.")

    benchmark_keys: list[tuple[str, str, str]] = []
    benchmark_counts: Counter[str] = Counter()
    normalized_benchmark_rows: list[tuple[object, ...]] = []
    for row in benchmark_rows:
        _required(row, "benchmark_symbol", "observation_date", "close", "source")
        symbol = row["benchmark_symbol"].strip()
        if symbol not in expected_benchmarks:
            raise RuntimeError(f"Unknown benchmark symbol in history evidence: {symbol}")
        source = row["source"].strip()
        key = (symbol, row["observation_date"].strip(), source)
        benchmark_keys.append(key)
        benchmark_counts[symbol] += 1
        normalized_benchmark_rows.append(
            (
                symbol,
                row["observation_date"].strip(),
                float(row["close"]),
                source,
                "2026-08-24T00:00:00+00:00",
                "metals-market-history-ingestion-rehearsal",
            )
        )
    if len(benchmark_keys) != len(set(benchmark_keys)):
        raise RuntimeError("Benchmark market history contains duplicate primary keys.")
    if set(benchmark_counts) != set(expected_benchmarks):
        raise RuntimeError("Benchmark history does not cover exactly the governed benchmark symbols.")
    if any(count < MIN_ROWS for count in benchmark_counts.values()):
        raise RuntimeError("Benchmark history is below the governed minimum row depth.")

    with tempfile.TemporaryDirectory(prefix="uip-metals-history-") as temp_root:
        database_path = Path(temp_root) / "metals_history_rehearsal.sqlite3"
        connection = sqlite3.connect(database_path)
        try:
            store = MetalsNativeStore(connection, parameter_style="qmark")
            store.initialize()
            inserted_vehicle = store.upsert_vehicle_observations(vehicle_objects)
            connection.execute(
                """CREATE TABLE metals_market_benchmark_observations (
                    benchmark_symbol TEXT NOT NULL,
                    observation_date TEXT NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    source TEXT NOT NULL,
                    collected_at_utc TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    PRIMARY KEY (benchmark_symbol, observation_date, source)
                )"""
            )
            connection.executemany(
                """INSERT INTO metals_market_benchmark_observations (
                    benchmark_symbol, observation_date, close, source, collected_at_utc, run_id
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                normalized_benchmark_rows,
            )
            connection.commit()

            vehicle_count = int(connection.execute("SELECT COUNT(*) FROM metals_vehicle_observations").fetchone()[0])
            benchmark_count = int(connection.execute("SELECT COUNT(*) FROM metals_market_benchmark_observations").fetchone()[0])
            vehicle_duplicate_count = int(connection.execute(
                """SELECT COUNT(*) FROM (
                    SELECT ticker, observation_date, source, COUNT(*) c
                    FROM metals_vehicle_observations GROUP BY ticker, observation_date, source HAVING c > 1
                )"""
            ).fetchone()[0])
            benchmark_duplicate_count = int(connection.execute(
                """SELECT COUNT(*) FROM (
                    SELECT benchmark_symbol, observation_date, source, COUNT(*) c
                    FROM metals_market_benchmark_observations GROUP BY benchmark_symbol, observation_date, source HAVING c > 1
                )"""
            ).fetchone()[0])
            latest_vehicle = {
                str(ticker): {"observation_date": str(observation_date), "close": float(close)}
                for ticker, observation_date, close in connection.execute(
                    """SELECT v.ticker, v.observation_date, v.close
                       FROM metals_vehicle_observations v
                       JOIN (SELECT ticker, MAX(observation_date) d FROM metals_vehicle_observations GROUP BY ticker) x
                         ON x.ticker=v.ticker AND x.d=v.observation_date
                       ORDER BY v.ticker"""
                ).fetchall()
            }
            latest_benchmark = {
                str(symbol): {"observation_date": str(observation_date), "close": float(close)}
                for symbol, observation_date, close in connection.execute(
                    """SELECT b.benchmark_symbol, b.observation_date, b.close
                       FROM metals_market_benchmark_observations b
                       JOIN (SELECT benchmark_symbol, MAX(observation_date) d FROM metals_market_benchmark_observations GROUP BY benchmark_symbol) x
                         ON x.benchmark_symbol=b.benchmark_symbol AND x.d=b.observation_date
                       ORDER BY b.benchmark_symbol"""
                ).fetchall()
            }
        finally:
            connection.close()

    if inserted_vehicle != len(vehicle_rows) or vehicle_count != len(vehicle_rows):
        raise RuntimeError("Isolated vehicle-history ingestion did not reconcile exactly.")
    if benchmark_count != len(benchmark_rows):
        raise RuntimeError("Isolated benchmark-history ingestion did not reconcile exactly.")
    if vehicle_duplicate_count or benchmark_duplicate_count:
        raise RuntimeError("Duplicate keys appeared after isolated history ingestion.")
    if set(latest_vehicle) != set(enabled_tickers):
        raise RuntimeError("Current vehicle-price selection did not cover all enabled vehicles.")
    if set(latest_benchmark) != set(expected_benchmarks):
        raise RuntimeError("Current benchmark-price selection did not cover all governed benchmarks.")

    result = {
        "status": "PASS",
        "rehearsal_only": True,
        "contract_id": EXPECTED_CONTRACT_ID,
        "vehicle_rows_ingested": vehicle_count,
        "benchmark_rows_ingested": benchmark_count,
        "vehicle_primary_key_duplicates": vehicle_duplicate_count,
        "benchmark_primary_key_duplicates": benchmark_duplicate_count,
        "vehicle_series_count": len(vehicle_counts),
        "benchmark_series_count": len(benchmark_counts),
        "latest_vehicle_prices": latest_vehicle,
        "latest_benchmark_prices": latest_benchmark,
        "production_database_write_authorized": False,
        "forecast_refresh_authorized": False,
        "model_retraining_authorized": False,
        "momentum_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": "AUTHORIZE_METALS_MARKET_HISTORY_PRODUCTION_SCHEMA_AND_INGESTION",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
