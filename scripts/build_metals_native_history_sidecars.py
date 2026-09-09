"""Build rich Metals history/current-price sidecars from UIP-owned PostgreSQL authority.

This script is intentionally read-only with respect to PostgreSQL. It materializes
CSV/JSON evidence files only and does not stage or activate a presentation publication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "foundation" / "production" / "metals_registry.py"
_REGISTRY_MODULE_NAME = "uip_metals_registry_direct"
_registry_spec = importlib.util.spec_from_file_location(_REGISTRY_MODULE_NAME, REGISTRY_PATH)
if _registry_spec is None or _registry_spec.loader is None:
    raise RuntimeError(f"Unable to load Metals registry module from {REGISTRY_PATH}")
_registry_module = importlib.util.module_from_spec(_registry_spec)
sys.modules[_REGISTRY_MODULE_NAME] = _registry_module
_registry_spec.loader.exec_module(_registry_module)
load_metals_registry = _registry_module.load_metals_registry

SOURCE_AUTHORITY = "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1"
PRICE_SEMANTICS = "UNADJUSTED_CLOSE"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_rows(db) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    registry = load_metals_registry()
    vehicles = {ticker: vehicle for ticker, vehicle in registry.vehicles_by_ticker.items() if vehicle.enabled}
    expected_tickers = set(vehicles)

    with db.cursor() as cur:
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute(
            """
            SELECT ticker, observation_date, close, adjusted_close, volume,
                   source, collected_at_utc, run_id
            FROM metals_vehicle_observations
            ORDER BY ticker, observation_date, source
            """
        )
        raw_rows = cur.fetchall()

    if not raw_rows:
        raise RuntimeError("metals_vehicle_observations is empty")

    observed_tickers = {str(row[0]) for row in raw_rows}
    unknown = sorted(observed_tickers - expected_tickers)
    missing = sorted(expected_tickers - observed_tickers)
    if unknown:
        raise RuntimeError(f"Unregistered Metals vehicle tickers observed: {unknown}")
    if missing:
        raise RuntimeError(f"Enabled Metals vehicle tickers missing from authority: {missing}")

    history: list[dict[str, object]] = []
    by_ticker: dict[str, list[dict[str, object]]] = defaultdict(list)
    for ticker, observation_date, close, adjusted_close, volume, source, collected_at_utc, run_id in raw_rows:
        ticker = str(ticker)
        vehicle = vehicles[ticker]
        row = {
            "asset_id": vehicle.vehicle_id,
            "ticker": ticker,
            "observation_date": str(observation_date),
            "close_usd": float(close),
            "adjusted_close_usd": "" if adjusted_close is None else float(adjusted_close),
            "volume": "" if volume is None else float(volume),
            "price_semantics": PRICE_SEMANTICS,
            "source_system": str(source),
            "source_authority": SOURCE_AUTHORITY,
            "source_package_id": f"metals-native-history-{str(observation_date)}",
            "source_run_id": str(run_id),
            "collected_at_utc": str(collected_at_utc),
        }
        history.append(row)
        by_ticker[ticker].append(row)

    current: list[dict[str, object]] = []
    for ticker in sorted(expected_tickers):
        latest = max(by_ticker[ticker], key=lambda row: (str(row["observation_date"]), str(row["source_system"])))
        current.append({
            "asset_id": latest["asset_id"],
            "ticker": ticker,
            "observation_date": latest["observation_date"],
            "current_price_usd": latest["close_usd"],
            "price_semantics": PRICE_SEMANTICS,
            "source_system": latest["source_system"],
            "source_authority": SOURCE_AUTHORITY,
            "source_package_id": latest["source_package_id"],
            "source_run_id": latest["source_run_id"],
            "collected_at_utc": latest["collected_at_utc"],
        })

    if len(current) != len(expected_tickers):
        raise RuntimeError("Current-price sidecar does not contain exactly one row per enabled vehicle")

    summary = {
        "status": "METALS_NATIVE_HISTORY_SIDECARS_PASS",
        "source_table": "metals_vehicle_observations",
        "source_authority": SOURCE_AUTHORITY,
        "history_row_count": len(history),
        "current_price_row_count": len(current),
        "enabled_vehicle_count": len(expected_tickers),
        "first_observation_date": min(str(row["observation_date"]) for row in history),
        "last_observation_date": max(str(row["observation_date"]) for row in history),
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
    }
    return history, current, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    output = args.output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(dsn) as db:
        history, current, summary = build_rows(db)
        db.rollback()

    history_path = output / "metals_price_history.csv"
    current_path = output / "metals_current_price.csv"
    _write_csv(history_path, list(history[0].keys()), history)
    _write_csv(current_path, list(current[0].keys()), current)

    manifest = {
        **summary,
        "files": {
            "metals_price_history.csv": {
                "row_count": len(history),
                "sha256": _sha256(history_path),
            },
            "metals_current_price.csv": {
                "row_count": len(current),
                "sha256": _sha256(current_path),
            },
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_HISTORY_SIDECARS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
