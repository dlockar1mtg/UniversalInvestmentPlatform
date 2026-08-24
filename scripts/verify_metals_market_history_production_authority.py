from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_registry import load_metals_registry  # noqa: E402
from scripts.collect_metals_daily_market_input import BENCHMARKS  # noqa: E402

EXPECTED_CONTRACT_ID = "METALS-MARKET-HISTORY-1"
EXPECTED_SOURCE = "yfinance"
EXPECTED_RUN_ID = "metals-market-history-backfill-20260824"
EXPECTED_VEHICLE_ROWS = 8283
EXPECTED_BENCHMARK_ROWS = 4522
EXPECTED_VEHICLE_SERIES = 11
EXPECTED_BENCHMARK_SERIES = 6
MIN_ROWS_PER_SERIES = 500


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scalar(connection, sql: str, params: tuple[object, ...] = ()) -> object:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Query returned no row: {sql}")
    return row[0]


def _rows(connection, sql: str, params: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return list(cursor.fetchall())


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify production Metals three-year market-history authority read-only.")
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--expected-vehicle-sha256", required=True)
    parser.add_argument("--expected-benchmark-sha256", required=True)
    parser.add_argument("--expected-summary-sha256", required=True)
    args = parser.parse_args()

    database_url = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("UIIP_DATABASE_URL is required.")

    evidence_root = args.evidence_root.resolve()
    vehicle_path = evidence_root / "vehicle_history.csv"
    benchmark_path = evidence_root / "benchmark_market_history.csv"
    summary_path = evidence_root / "summary.json"
    for path in (vehicle_path, benchmark_path, summary_path):
        if not path.is_file():
            raise RuntimeError(f"Required certified evidence is missing: {path}")

    actual_hashes = {
        "vehicle": _sha256(vehicle_path),
        "benchmark": _sha256(benchmark_path),
        "summary": _sha256(summary_path),
    }
    expected_hashes = {
        "vehicle": args.expected_vehicle_sha256.lower(),
        "benchmark": args.expected_benchmark_sha256.lower(),
        "summary": args.expected_summary_sha256.lower(),
    }
    if actual_hashes != expected_hashes:
        raise RuntimeError(f"Certified evidence SHA-256 mismatch: actual={actual_hashes}; expected={expected_hashes}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS" or summary.get("contract_id") != EXPECTED_CONTRACT_ID:
        raise RuntimeError("Evidence summary is not a passing METALS-MARKET-HISTORY-1 package.")
    if int(summary.get("vehicle_row_count") or -1) != EXPECTED_VEHICLE_ROWS:
        raise RuntimeError("Evidence vehicle row count changed unexpectedly.")
    if int(summary.get("benchmark_row_count") or -1) != EXPECTED_BENCHMARK_ROWS:
        raise RuntimeError("Evidence benchmark row count changed unexpectedly.")

    registry = load_metals_registry()
    enabled_tickers = tuple(sorted(vehicle.ticker for vehicle in registry.vehicles if vehicle.enabled))
    expected_tickers = tuple(sorted(BENCHMARKS))
    if enabled_tickers != expected_tickers or len(enabled_tickers) != EXPECTED_VEHICLE_SERIES:
        raise RuntimeError("Enabled Metals vehicle registry does not match the governed market-history contract.")
    expected_benchmarks = tuple(sorted(set(BENCHMARKS.values())))
    if len(expected_benchmarks) != EXPECTED_BENCHMARK_SERIES:
        raise RuntimeError("Governed benchmark map no longer contains exactly six market benchmarks.")

    import psycopg

    connection = psycopg.connect(database_url)
    try:
        connection.execute("BEGIN TRANSACTION READ ONLY")

        vehicle_rows = int(_scalar(connection, "SELECT COUNT(*) FROM metals_vehicle_observations WHERE source=%s", (EXPECTED_SOURCE,)))
        benchmark_rows = int(_scalar(connection, "SELECT COUNT(*) FROM metals_market_benchmark_observations WHERE source=%s", (EXPECTED_SOURCE,)))
        if vehicle_rows != EXPECTED_VEHICLE_ROWS:
            raise RuntimeError(f"Unexpected production yfinance vehicle rows: {vehicle_rows}")
        if benchmark_rows != EXPECTED_BENCHMARK_ROWS:
            raise RuntimeError(f"Unexpected production yfinance benchmark rows: {benchmark_rows}")

        vehicle_run_rows = int(_scalar(connection, "SELECT COUNT(*) FROM metals_vehicle_observations WHERE source=%s AND run_id=%s", (EXPECTED_SOURCE, EXPECTED_RUN_ID)))
        benchmark_run_rows = int(_scalar(connection, "SELECT COUNT(*) FROM metals_market_benchmark_observations WHERE source=%s AND run_id=%s", (EXPECTED_SOURCE, EXPECTED_RUN_ID)))
        if vehicle_run_rows != EXPECTED_VEHICLE_ROWS or benchmark_run_rows != EXPECTED_BENCHMARK_ROWS:
            raise RuntimeError("Production history run lineage does not reconcile to the certified backfill run.")

        vehicle_dupes = int(_scalar(connection, """SELECT COUNT(*) FROM (
            SELECT ticker, observation_date, source, COUNT(*) c
            FROM metals_vehicle_observations
            WHERE source=%s
            GROUP BY ticker, observation_date, source
            HAVING COUNT(*) > 1
        ) q""", (EXPECTED_SOURCE,)))
        benchmark_dupes = int(_scalar(connection, """SELECT COUNT(*) FROM (
            SELECT benchmark_symbol, observation_date, source, COUNT(*) c
            FROM metals_market_benchmark_observations
            WHERE source=%s
            GROUP BY benchmark_symbol, observation_date, source
            HAVING COUNT(*) > 1
        ) q""", (EXPECTED_SOURCE,)))
        if vehicle_dupes or benchmark_dupes:
            raise RuntimeError("Duplicate primary-key groups exist in production market history.")

        vehicle_coverage_rows = _rows(connection, """SELECT ticker, COUNT(*), MIN(observation_date), MAX(observation_date),
            COUNT(adjusted_close), COUNT(volume)
            FROM metals_vehicle_observations
            WHERE source=%s
            GROUP BY ticker ORDER BY ticker""", (EXPECTED_SOURCE,))
        benchmark_coverage_rows = _rows(connection, """SELECT benchmark_symbol, COUNT(*), MIN(observation_date), MAX(observation_date)
            FROM metals_market_benchmark_observations
            WHERE source=%s
            GROUP BY benchmark_symbol ORDER BY benchmark_symbol""", (EXPECTED_SOURCE,))

        vehicle_coverage = []
        for ticker, count, min_date, max_date, adjusted_count, volume_count in vehicle_coverage_rows:
            vehicle_coverage.append({
                "ticker": str(ticker),
                "row_count": int(count),
                "min_observation_date": str(min_date),
                "max_observation_date": str(max_date),
                "adjusted_close_populated": int(adjusted_count),
                "volume_populated": int(volume_count),
            })
        benchmark_coverage = [
            {
                "benchmark_symbol": str(symbol),
                "row_count": int(count),
                "min_observation_date": str(min_date),
                "max_observation_date": str(max_date),
            }
            for symbol, count, min_date, max_date in benchmark_coverage_rows
        ]

        if tuple(item["ticker"] for item in vehicle_coverage) != enabled_tickers:
            raise RuntimeError("Production vehicle-history series do not match enabled registry tickers.")
        if tuple(item["benchmark_symbol"] for item in benchmark_coverage) != expected_benchmarks:
            raise RuntimeError("Production benchmark-history series do not match governed benchmark symbols.")
        if any(item["row_count"] < MIN_ROWS_PER_SERIES for item in vehicle_coverage):
            raise RuntimeError("At least one production vehicle-history series is below the governed depth minimum.")
        if any(item["row_count"] < MIN_ROWS_PER_SERIES for item in benchmark_coverage):
            raise RuntimeError("At least one production benchmark-history series is below the governed depth minimum.")

        latest_vehicle_rows = _rows(connection, """SELECT v.ticker, v.observation_date, v.close
            FROM metals_vehicle_observations v
            JOIN (
                SELECT ticker, MAX(observation_date) d
                FROM metals_vehicle_observations
                WHERE source=%s GROUP BY ticker
            ) x ON x.ticker=v.ticker AND x.d=v.observation_date
            WHERE v.source=%s ORDER BY v.ticker""", (EXPECTED_SOURCE, EXPECTED_SOURCE))
        latest_benchmark_rows = _rows(connection, """SELECT b.benchmark_symbol, b.observation_date, b.close
            FROM metals_market_benchmark_observations b
            JOIN (
                SELECT benchmark_symbol, MAX(observation_date) d
                FROM metals_market_benchmark_observations
                WHERE source=%s GROUP BY benchmark_symbol
            ) x ON x.benchmark_symbol=b.benchmark_symbol AND x.d=b.observation_date
            WHERE b.source=%s ORDER BY b.benchmark_symbol""", (EXPECTED_SOURCE, EXPECTED_SOURCE))

        latest_vehicle_prices = {
            str(ticker): {"observation_date": str(observation_date), "close": float(close)}
            for ticker, observation_date, close in latest_vehicle_rows
        }
        latest_benchmark_prices = {
            str(symbol): {"observation_date": str(observation_date), "close": float(close)}
            for symbol, observation_date, close in latest_benchmark_rows
        }
        if set(latest_vehicle_prices) != set(enabled_tickers):
            raise RuntimeError("Production latest vehicle-price resolution is incomplete.")
        if set(latest_benchmark_prices) != set(expected_benchmarks):
            raise RuntimeError("Production latest benchmark-price resolution is incomplete.")
        if any(item["close"] <= 0 for item in latest_vehicle_prices.values()):
            raise RuntimeError("Production latest vehicle prices contain a non-positive value.")
        if any(item["close"] <= 0 for item in latest_benchmark_prices.values()):
            raise RuntimeError("Production latest benchmark prices contain a non-positive value.")

        connection.rollback()
    finally:
        connection.close()

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": EXPECTED_CONTRACT_ID,
        "source": EXPECTED_SOURCE,
        "run_id": EXPECTED_RUN_ID,
        "vehicle_evidence_sha256": actual_hashes["vehicle"],
        "benchmark_evidence_sha256": actual_hashes["benchmark"],
        "summary_evidence_sha256": actual_hashes["summary"],
        "vehicle_rows_verified": vehicle_rows,
        "benchmark_rows_verified": benchmark_rows,
        "vehicle_primary_key_duplicates": vehicle_dupes,
        "benchmark_primary_key_duplicates": benchmark_dupes,
        "vehicle_coverage": vehicle_coverage,
        "benchmark_coverage": benchmark_coverage,
        "latest_vehicle_prices": latest_vehicle_prices,
        "latest_benchmark_prices": latest_benchmark_prices,
        "current_price_authority_verified": True,
        "historical_price_authority_verified": True,
        "momentum_feature_calculation_authorized": True,
        "forecast_refresh_authorized": False,
        "model_retraining_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": "AUTHORIZE_METALS_MOMENTUM_FEATURE_REHEARSAL",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
