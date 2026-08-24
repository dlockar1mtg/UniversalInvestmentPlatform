from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_registry import load_metals_registry
from scripts.collect_metals_daily_market_input import BENCHMARKS

EXPECTED_CONTRACT_ID = "METALS-MARKET-HISTORY-1"
EXPECTED_VEHICLE_ROWS = 8283
EXPECTED_BENCHMARK_ROWS = 4522
EXPECTED_VEHICLES = 11
EXPECTED_BENCHMARKS = 6
SOURCE = "yfinance"
RUN_ID = "metals-market-history-backfill-20260824"
COLLECTED_AT_UTC = "2026-08-24T00:00:00+00:00"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"Required market-history evidence is missing: {path}")
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
    parser = argparse.ArgumentParser(description="Promote certified Metals three-year market history into the UIP-owned PostgreSQL native store.")
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--expected-vehicle-sha256", required=True)
    parser.add_argument("--expected-benchmark-sha256", required=True)
    parser.add_argument("--expected-summary-sha256", required=True)
    args = parser.parse_args()

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is not available in this process.")

    root = args.evidence_root.resolve()
    vehicle_path = root / "vehicle_history.csv"
    benchmark_path = root / "benchmark_market_history.csv"
    summary_path = root / "summary.json"
    for path, expected in (
        (vehicle_path, args.expected_vehicle_sha256),
        (benchmark_path, args.expected_benchmark_sha256),
        (summary_path, args.expected_summary_sha256),
    ):
        actual = _sha256(path)
        if actual.lower() != expected.strip().lower():
            raise RuntimeError(f"Evidence SHA-256 changed for {path.name}: {actual}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS" or summary.get("contract_id") != EXPECTED_CONTRACT_ID:
        raise RuntimeError("Market-history evidence is not a PASS METALS-MARKET-HISTORY-1 rehearsal.")
    if summary.get("rehearsal_only") is not True:
        raise RuntimeError("Market-history source evidence is not marked rehearsal-only.")
    if int(summary.get("vehicle_row_count") or -1) != EXPECTED_VEHICLE_ROWS:
        raise RuntimeError("Certified vehicle-history row count changed.")
    if int(summary.get("benchmark_row_count") or -1) != EXPECTED_BENCHMARK_ROWS:
        raise RuntimeError("Certified benchmark-history row count changed.")

    vehicle_rows = _read_csv(vehicle_path)
    benchmark_rows = _read_csv(benchmark_path)
    if len(vehicle_rows) != EXPECTED_VEHICLE_ROWS or len(benchmark_rows) != EXPECTED_BENCHMARK_ROWS:
        raise RuntimeError("Evidence CSV populations do not match certified counts.")

    registry = load_metals_registry()
    enabled_tickers = tuple(sorted(vehicle.ticker for vehicle in registry.vehicles if vehicle.enabled))
    expected_tickers = tuple(sorted(BENCHMARKS))
    expected_benchmarks = tuple(sorted(set(BENCHMARKS.values())))
    if enabled_tickers != expected_tickers or len(enabled_tickers) != EXPECTED_VEHICLES:
        raise RuntimeError("Enabled Metals registry does not match the governed vehicle history universe.")
    if len(expected_benchmarks) != EXPECTED_BENCHMARKS:
        raise RuntimeError("Governed benchmark map does not contain six unique symbols.")

    vehicle_values: list[tuple[object, ...]] = []
    vehicle_keys: list[tuple[str, str, str]] = []
    vehicle_counts: Counter[str] = Counter()
    for row in vehicle_rows:
        _required(row, "ticker", "observation_date", "close", "source")
        ticker = row["ticker"].strip().upper()
        source = row["source"].strip()
        if ticker not in enabled_tickers or source != SOURCE:
            raise RuntimeError(f"Unexpected vehicle history identity/source: {ticker}/{source}")
        key = (ticker, row["observation_date"].strip(), source)
        vehicle_keys.append(key)
        vehicle_counts[ticker] += 1
        vehicle_values.append((
            ticker,
            row["observation_date"].strip(),
            float(row["close"]),
            _optional_float(row.get("adjusted_close", "")),
            _optional_float(row.get("volume", "")),
            source,
            COLLECTED_AT_UTC,
            RUN_ID,
        ))
    if len(vehicle_keys) != len(set(vehicle_keys)) or set(vehicle_counts) != set(enabled_tickers):
        raise RuntimeError("Vehicle history keys or coverage changed from the certified rehearsal.")

    benchmark_values: list[tuple[object, ...]] = []
    benchmark_keys: list[tuple[str, str, str]] = []
    benchmark_counts: Counter[str] = Counter()
    for row in benchmark_rows:
        _required(row, "benchmark_symbol", "observation_date", "close", "source")
        symbol = row["benchmark_symbol"].strip()
        source = row["source"].strip()
        if symbol not in expected_benchmarks or source != SOURCE:
            raise RuntimeError(f"Unexpected benchmark history identity/source: {symbol}/{source}")
        key = (symbol, row["observation_date"].strip(), source)
        benchmark_keys.append(key)
        benchmark_counts[symbol] += 1
        benchmark_values.append((
            symbol,
            row["observation_date"].strip(),
            float(row["close"]),
            source,
            COLLECTED_AT_UTC,
            RUN_ID,
        ))
    if len(benchmark_keys) != len(set(benchmark_keys)) or set(benchmark_counts) != set(expected_benchmarks):
        raise RuntimeError("Benchmark history keys or coverage changed from the certified rehearsal.")

    import psycopg

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.metals_vehicle_observations')")
            if cursor.fetchone()[0] is None:
                raise RuntimeError("Existing UIP-owned metals_vehicle_observations table is missing.")

            cursor.execute("SELECT COUNT(*) FROM metals_vehicle_observations WHERE source <> %s", (SOURCE,))
            non_yfinance_vehicle_before = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM metals_vehicle_observations WHERE source = %s", (SOURCE,))
            yfinance_vehicle_before = int(cursor.fetchone()[0])

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS metals_market_benchmark_observations (
                    benchmark_symbol TEXT NOT NULL,
                    observation_date TEXT NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    source TEXT NOT NULL,
                    collected_at_utc TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    PRIMARY KEY (benchmark_symbol, observation_date, source)
                )"""
            )
            cursor.execute("SELECT COUNT(*) FROM metals_market_benchmark_observations WHERE source <> %s", (SOURCE,))
            non_yfinance_benchmark_before = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM metals_market_benchmark_observations WHERE source = %s", (SOURCE,))
            yfinance_benchmark_before = int(cursor.fetchone()[0])

            cursor.executemany(
                """INSERT INTO metals_vehicle_observations (
                    ticker, observation_date, close, adjusted_close, volume, source, collected_at_utc, run_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, observation_date, source) DO UPDATE SET
                    close=EXCLUDED.close,
                    adjusted_close=EXCLUDED.adjusted_close,
                    volume=EXCLUDED.volume,
                    collected_at_utc=EXCLUDED.collected_at_utc,
                    run_id=EXCLUDED.run_id""",
                vehicle_values,
            )
            cursor.executemany(
                """INSERT INTO metals_market_benchmark_observations (
                    benchmark_symbol, observation_date, close, source, collected_at_utc, run_id
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (benchmark_symbol, observation_date, source) DO UPDATE SET
                    close=EXCLUDED.close,
                    collected_at_utc=EXCLUDED.collected_at_utc,
                    run_id=EXCLUDED.run_id""",
                benchmark_values,
            )

            cursor.execute("SELECT COUNT(*) FROM metals_vehicle_observations WHERE source = %s", (SOURCE,))
            yfinance_vehicle_after = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM metals_market_benchmark_observations WHERE source = %s", (SOURCE,))
            yfinance_benchmark_after = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM metals_vehicle_observations WHERE source <> %s", (SOURCE,))
            non_yfinance_vehicle_after = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM metals_market_benchmark_observations WHERE source <> %s", (SOURCE,))
            non_yfinance_benchmark_after = int(cursor.fetchone()[0])

            if yfinance_vehicle_after != EXPECTED_VEHICLE_ROWS:
                raise RuntimeError(f"Production yfinance vehicle-history population did not reconcile: {yfinance_vehicle_after}")
            if yfinance_benchmark_after != EXPECTED_BENCHMARK_ROWS:
                raise RuntimeError(f"Production yfinance benchmark-history population did not reconcile: {yfinance_benchmark_after}")
            if non_yfinance_vehicle_after != non_yfinance_vehicle_before:
                raise RuntimeError("Production promotion changed non-yfinance vehicle-history rows.")
            if non_yfinance_benchmark_after != non_yfinance_benchmark_before:
                raise RuntimeError("Production promotion changed non-yfinance benchmark-history rows.")

            cursor.execute(
                """SELECT COUNT(*) FROM (
                    SELECT ticker, observation_date, source, COUNT(*) c
                    FROM metals_vehicle_observations
                    WHERE source=%s
                    GROUP BY ticker, observation_date, source HAVING COUNT(*) > 1
                ) d""",
                (SOURCE,),
            )
            vehicle_duplicates = int(cursor.fetchone()[0])
            cursor.execute(
                """SELECT COUNT(*) FROM (
                    SELECT benchmark_symbol, observation_date, source, COUNT(*) c
                    FROM metals_market_benchmark_observations
                    WHERE source=%s
                    GROUP BY benchmark_symbol, observation_date, source HAVING COUNT(*) > 1
                ) d""",
                (SOURCE,),
            )
            benchmark_duplicates = int(cursor.fetchone()[0])
            if vehicle_duplicates or benchmark_duplicates:
                raise RuntimeError("Duplicate primary keys appeared during production market-history promotion.")

            cursor.execute(
                """SELECT v.ticker, v.observation_date, v.close
                   FROM metals_vehicle_observations v
                   JOIN (
                       SELECT ticker, MAX(observation_date) d
                       FROM metals_vehicle_observations WHERE source=%s GROUP BY ticker
                   ) x ON x.ticker=v.ticker AND x.d=v.observation_date
                   WHERE v.source=%s ORDER BY v.ticker""",
                (SOURCE, SOURCE),
            )
            latest_vehicle = {
                str(ticker): {"observation_date": str(observation_date), "close": float(close)}
                for ticker, observation_date, close in cursor.fetchall()
            }
            cursor.execute(
                """SELECT b.benchmark_symbol, b.observation_date, b.close
                   FROM metals_market_benchmark_observations b
                   JOIN (
                       SELECT benchmark_symbol, MAX(observation_date) d
                       FROM metals_market_benchmark_observations WHERE source=%s GROUP BY benchmark_symbol
                   ) x ON x.benchmark_symbol=b.benchmark_symbol AND x.d=b.observation_date
                   WHERE b.source=%s ORDER BY b.benchmark_symbol""",
                (SOURCE, SOURCE),
            )
            latest_benchmark = {
                str(symbol): {"observation_date": str(observation_date), "close": float(close)}
                for symbol, observation_date, close in cursor.fetchall()
            }
            if set(latest_vehicle) != set(enabled_tickers) or set(latest_benchmark) != set(expected_benchmarks):
                raise RuntimeError("Production current-price resolution is incomplete after market-history promotion.")

    result = {
        "status": "PASS",
        "mode": "PRODUCTION_SCHEMA_AND_INGESTION",
        "contract_id": EXPECTED_CONTRACT_ID,
        "run_id": RUN_ID,
        "source": SOURCE,
        "vehicle_evidence_sha256": _sha256(vehicle_path),
        "benchmark_evidence_sha256": _sha256(benchmark_path),
        "summary_evidence_sha256": _sha256(summary_path),
        "vehicle_rows_certified": EXPECTED_VEHICLE_ROWS,
        "benchmark_rows_certified": EXPECTED_BENCHMARK_ROWS,
        "vehicle_rows_before_for_source": yfinance_vehicle_before,
        "benchmark_rows_before_for_source": yfinance_benchmark_before,
        "vehicle_rows_after_for_source": yfinance_vehicle_after,
        "benchmark_rows_after_for_source": yfinance_benchmark_after,
        "vehicle_primary_key_duplicates": vehicle_duplicates,
        "benchmark_primary_key_duplicates": benchmark_duplicates,
        "latest_vehicle_prices": latest_vehicle,
        "latest_benchmark_prices": latest_benchmark,
        "production_database_write_executed": True,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "momentum_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": "VERIFY_METALS_MARKET_HISTORY_PRODUCTION_AUTHORITY",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
