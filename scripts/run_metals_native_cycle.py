"""Run the UIP-native Metals forecast and decision cycle."""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_native_cycle import (  # noqa: E402
    NativeObservation,
    evaluate_native_cycle,
    load_methodology,
    publish_native_cycle,
)


def _connect():
    database_url = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if database_url:
        import psycopg
        return psycopg.connect(database_url), "%s"
    path = ROOT / "data" / "operations" / "metals" / "metals_native.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path), "?"


def _load(connection) -> tuple[list[NativeObservation], list[NativeObservation]]:
    cursor = connection.cursor()
    benchmarks = [
        NativeObservation(str(row[0]), str(row[1]), float(row[2]), str(row[3]))
        for row in cursor.execute(
            "SELECT series_id, observation_date, value, source FROM metals_observations ORDER BY series_id, observation_date"
        ).fetchall()
    ]
    vehicles = [
        NativeObservation(str(row[0]), str(row[1]), float(row[2]), str(row[3]))
        for row in cursor.execute(
            "SELECT ticker, observation_date, COALESCE(adjusted_close, close), source FROM metals_vehicle_observations ORDER BY ticker, observation_date"
        ).fetchall()
    ]
    return benchmarks, vehicles


def main() -> int:
    parser = argparse.ArgumentParser(description="Run UIP-native Metals forecasts and recommendations.")
    parser.add_argument(
        "--methodology",
        type=Path,
        default=ROOT / "config" / "metals" / "model_methodology_registry.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data" / "operations" / "metals" / "native_cycle",
    )
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    connection, _ = _connect()
    try:
        benchmarks, vehicles = _load(connection)
    finally:
        connection.close()

    report = evaluate_native_cycle(benchmarks, vehicles, load_methodology(args.methodology))
    json_path, csv_path = publish_native_cycle(report, args.output_root)
    print(f"METALS NATIVE CYCLE: {report.status}")
    print(f"Forecasts: {report.forecast_count}")
    print(f"Assets: {report.asset_count}")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    if args.strict and report.status != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
