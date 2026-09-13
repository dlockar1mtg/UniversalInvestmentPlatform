"""Run the UIP-native Metals forecast and decision cycle."""
from __future__ import annotations

import argparse
import math
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
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

REL_TOL = 1e-9
ABS_TOL = 1e-8


def _connect():
    database_url = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if database_url:
        import psycopg
        return psycopg.connect(database_url), "%s"
    path = ROOT / "data" / "operations" / "metals" / "metals_native.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path), "?"


def _parse_timestamp(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError("missing collected_at_utc")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"invalid collected_at_utc: {text}") from exc
    if parsed.tzinfo is None:
        raise RuntimeError(f"collected_at_utc must be timezone-aware: {text}")
    return parsed


def _canonicalize(rows: list[tuple[object, ...]]) -> tuple[list[NativeObservation], int, int]:
    grouped: dict[tuple[str, str], list[tuple[object, ...]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row[0]), str(row[1]))].append(row)

    output: list[NativeObservation] = []
    collapsed = 0
    superseded_conflicts = 0
    for (asset_id, observation_date), candidates in sorted(grouped.items()):
        parsed = [(row, _parse_timestamp(row[4])) for row in candidates]
        latest_time = max(ts for _, ts in parsed)
        latest = [row for row, ts in parsed if ts == latest_time]
        chosen_value = float(latest[0][2])
        for row in latest[1:]:
            if not math.isclose(chosen_value, float(row[2]), rel_tol=REL_TOL, abs_tol=ABS_TOL):
                raise RuntimeError(
                    f"conflicting latest-timestamp source values for {asset_id} on {observation_date}"
                )
        chosen = sorted(latest, key=lambda row: (str(row[3]), str(row[5])))[0]
        collapsed += max(0, len(candidates) - 1)
        for row, ts in parsed:
            if row is chosen:
                continue
            if ts < latest_time and not math.isclose(float(row[2]), float(chosen[2]), rel_tol=REL_TOL, abs_tol=ABS_TOL):
                superseded_conflicts += 1
        output.append(NativeObservation(asset_id, observation_date, float(chosen[2]), str(chosen[3])))
    return output, collapsed, superseded_conflicts


def _load(connection) -> tuple[list[NativeObservation], list[NativeObservation]]:
    cursor = connection.cursor()
    benchmark_rows = cursor.execute(
        "SELECT series_id, observation_date, value, source, collected_at_utc, run_id FROM metals_observations ORDER BY series_id, observation_date, source"
    ).fetchall()
    vehicle_rows = cursor.execute(
        "SELECT ticker, observation_date, COALESCE(adjusted_close, close), source, collected_at_utc, run_id FROM metals_vehicle_observations ORDER BY ticker, observation_date, source"
    ).fetchall()
    benchmarks, benchmark_collapsed, benchmark_superseded = _canonicalize(list(benchmark_rows))
    vehicles, vehicle_collapsed, vehicle_superseded = _canonicalize(list(vehicle_rows))
    print("METALS_NATIVE_OBSERVATION_RECONCILIATION=LATEST_COLLECTED_REVISION_WINS")
    print(f"Benchmark duplicate source rows collapsed: {benchmark_collapsed}")
    print(f"Benchmark superseded conflicting revisions: {benchmark_superseded}")
    print(f"Vehicle duplicate source rows collapsed: {vehicle_collapsed}")
    print(f"Vehicle superseded conflicting revisions: {vehicle_superseded}")
    return benchmarks, vehicles


def main() -> int:
    parser = argparse.ArgumentParser(description="Run UIP-native Metals forecasts and recommendations.")
    parser.add_argument("--methodology", type=Path, default=ROOT / "config" / "metals" / "model_methodology_registry.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data" / "operations" / "metals" / "native_cycle")
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
