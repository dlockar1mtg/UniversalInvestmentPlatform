from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_registry import load_metals_registry


def _iso(value: object) -> str | None:
    return None if value is None else str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of Metals benchmark and vehicle market-history authority.")
    parser.parse_args()

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is not available in this process.")

    import psycopg

    registry = load_metals_registry()
    enabled_vehicles = {v.ticker: v for v in registry.vehicles if v.enabled}
    known_assets = {a.asset_id: a for a in registry.assets}

    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.metals_observations'), to_regclass('public.metals_vehicle_observations'), to_regclass('public.metals_native_runs')")
        tables = cursor.fetchone()
        if not tables or any(value is None for value in tables):
            raise RuntimeError(f"Required Metals native history tables are missing: {tables}")

        cursor.execute("SELECT COUNT(*), MIN(observation_date), MAX(observation_date), COUNT(DISTINCT series_id), COUNT(DISTINCT source) FROM metals_observations")
        benchmark_summary = cursor.fetchone()
        cursor.execute("SELECT COUNT(*), MIN(observation_date), MAX(observation_date), COUNT(DISTINCT ticker), COUNT(DISTINCT source) FROM metals_vehicle_observations")
        vehicle_summary = cursor.fetchone()
        cursor.execute("SELECT series_id, COUNT(*), MIN(observation_date), MAX(observation_date), COUNT(DISTINCT source) FROM metals_observations GROUP BY series_id ORDER BY series_id")
        benchmark_rows = cursor.fetchall()
        cursor.execute("SELECT ticker, COUNT(*), MIN(observation_date), MAX(observation_date), COUNT(DISTINCT source), COUNT(adjusted_close), COUNT(volume) FROM metals_vehicle_observations GROUP BY ticker ORDER BY ticker")
        vehicle_rows = cursor.fetchall()
        cursor.execute("SELECT status, COUNT(*) FROM metals_native_runs GROUP BY status ORDER BY status")
        run_status_rows = cursor.fetchall()
        cursor.execute("SELECT run_id, started_at_utc, completed_at_utc, status, benchmark_rows, vehicle_rows FROM metals_native_runs ORDER BY started_at_utc DESC LIMIT 5")
        recent_runs = cursor.fetchall()

    vehicle_tickers = {str(row[0]) for row in vehicle_rows}
    unknown_vehicle_tickers = sorted(vehicle_tickers - set(enabled_vehicles))
    enabled_without_history = sorted(set(enabled_vehicles) - vehicle_tickers)

    by_underlying: dict[str, list[str]] = defaultdict(list)
    for ticker in sorted(vehicle_tickers & set(enabled_vehicles)):
        by_underlying[enabled_vehicles[ticker].underlying_asset_id].append(ticker)

    underlying_coverage = []
    for asset_id, asset in sorted(known_assets.items()):
        tickers = by_underlying.get(asset_id, [])
        underlying_coverage.append({
            "asset_id": asset_id,
            "asset_name": asset.name,
            "benchmark_vehicle": asset.benchmark_vehicle,
            "history_vehicle_count": len(tickers),
            "history_vehicles": tickers,
        })

    payload = {
        "status": "PASS",
        "read_only": True,
        "benchmark_history": {
            "row_count": int(benchmark_summary[0]),
            "min_observation_date": _iso(benchmark_summary[1]),
            "max_observation_date": _iso(benchmark_summary[2]),
            "series_count": int(benchmark_summary[3]),
            "source_count": int(benchmark_summary[4]),
            "series": [
                {
                    "series_id": str(row[0]),
                    "row_count": int(row[1]),
                    "min_observation_date": _iso(row[2]),
                    "max_observation_date": _iso(row[3]),
                    "source_count": int(row[4]),
                }
                for row in benchmark_rows
            ],
        },
        "vehicle_history": {
            "row_count": int(vehicle_summary[0]),
            "min_observation_date": _iso(vehicle_summary[1]),
            "max_observation_date": _iso(vehicle_summary[2]),
            "ticker_count": int(vehicle_summary[3]),
            "source_count": int(vehicle_summary[4]),
            "tickers": [
                {
                    "ticker": str(row[0]),
                    "row_count": int(row[1]),
                    "min_observation_date": _iso(row[2]),
                    "max_observation_date": _iso(row[3]),
                    "source_count": int(row[4]),
                    "adjusted_close_populated": int(row[5]),
                    "volume_populated": int(row[6]),
                }
                for row in vehicle_rows
            ],
        },
        "registry_reconciliation": {
            "enabled_vehicle_count": len(enabled_vehicles),
            "enabled_without_history": enabled_without_history,
            "unknown_history_tickers": unknown_vehicle_tickers,
            "underlying_coverage": underlying_coverage,
        },
        "native_run_status_counts": {str(status): int(count) for status, count in run_status_rows},
        "recent_native_runs": [
            {
                "run_id": str(row[0]),
                "started_at_utc": _iso(row[1]),
                "completed_at_utc": _iso(row[2]),
                "status": str(row[3]),
                "benchmark_rows": int(row[4]),
                "vehicle_rows": int(row[5]),
            }
            for row in recent_runs
        ],
        "current_price_authority_candidate": int(vehicle_summary[0]) > 0,
        "historical_chart_authority_candidate": int(vehicle_summary[0]) > int(vehicle_summary[3]),
        "benchmark_history_authority_candidate": int(benchmark_summary[0]) > 0,
        "momentum_policy_authorized": False,
        "tactical_posture_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": "ASSESS_METALS_MARKET_HISTORY_COVERAGE_FOR_AUTHORITY_BINDING",
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
