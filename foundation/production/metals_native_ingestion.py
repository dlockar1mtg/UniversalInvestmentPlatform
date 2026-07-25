"""Normalize UIP-owned Metals collection surfaces into the native store."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from foundation.production.metals_native_store import (
    MetalsNativeStore,
    MetalsObservation,
    MetalsVehicleObservation,
    utc_now_iso,
)


@dataclass(frozen=True)
class MetalsIngestionResult:
    run_id: str
    benchmark_rows: int
    vehicle_rows: int
    status: str


def _first(row: dict[str, str], *names: str, default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return default


def _optional_float(value: str) -> float | None:
    text = str(value or "").strip()
    return None if not text else float(text)


def load_benchmark_csv(path: Path, *, run_id: str, collected_at_utc: str | None = None) -> tuple[MetalsObservation, ...]:
    collected = collected_at_utc or utc_now_iso()
    rows: list[MetalsObservation] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            series_id = _first(raw, "series_id", "asset_id", "symbol", "metal")
            observation_date = _first(raw, "observation_date", "date", "data_as_of_date")
            value = _first(raw, "value", "price", "close", "latest_value")
            source = _first(raw, "source", "provider", "source_name")
            unit = _first(raw, "unit", "units", default="unknown")
            if not all((series_id, observation_date, value, source)):
                raise ValueError(f"Incomplete benchmark observation in {path}: {raw}")
            rows.append(MetalsObservation(series_id, observation_date, float(value), source, unit, collected, run_id))
    return tuple(rows)


def load_vehicle_csv(path: Path, *, run_id: str, collected_at_utc: str | None = None) -> tuple[MetalsVehicleObservation, ...]:
    collected = collected_at_utc or utc_now_iso()
    rows: list[MetalsVehicleObservation] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            ticker = _first(raw, "ticker", "symbol", "vehicle_id")
            observation_date = _first(raw, "observation_date", "date", "market_date")
            close = _first(raw, "close", "price", "market_price")
            source = _first(raw, "source", "provider", "source_name", default="universal-market-provider")
            if not all((ticker, observation_date, close)):
                raise ValueError(f"Incomplete vehicle observation in {path}: {raw}")
            rows.append(
                MetalsVehicleObservation(
                    ticker=ticker,
                    observation_date=observation_date,
                    close=float(close),
                    adjusted_close=_optional_float(_first(raw, "adjusted_close", "adj_close")),
                    volume=_optional_float(_first(raw, "volume")),
                    source=source,
                    collected_at_utc=collected,
                    run_id=run_id,
                )
            )
    return tuple(rows)


def ingest_collected_surfaces(
    store: MetalsNativeStore,
    *,
    run_id: str,
    benchmark_paths: Iterable[Path],
    vehicle_paths: Iterable[Path],
) -> MetalsIngestionResult:
    store.initialize()
    store.begin_run(run_id)
    benchmark_count = 0
    vehicle_count = 0
    try:
        for path in benchmark_paths:
            benchmark_count += store.upsert_benchmark_observations(load_benchmark_csv(path, run_id=run_id))
        for path in vehicle_paths:
            vehicle_count += store.upsert_vehicle_observations(load_vehicle_csv(path, run_id=run_id))
        store.complete_run(run_id, benchmark_rows=benchmark_count, vehicle_rows=vehicle_count)
        return MetalsIngestionResult(run_id, benchmark_count, vehicle_count, "PASS")
    except Exception as exc:
        store.fail_run(run_id, f"{type(exc).__name__}: {exc}")
        raise
