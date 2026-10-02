"""Backfill daily price history for registered Metals vehicles.

New vehicles start with no history, so their risk and liquidity evidence would be
meaningless for weeks. This writes a vehicle CSV in the shape the daily collector
produces (close, adjusted close, real daily volume) for the requested registered
tickers; the existing ingest step then loads it:

    python scripts/backfill_metals_vehicle_history.py --tickers GLDM
    python scripts/ingest_metals_native_observations.py --vehicle <output> --run-id ...
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "metals" / "vehicles.json"
DEFAULT_OUTPUT = ROOT / "data" / "operations" / "metals" / "vehicle_history_backfill.csv"
FIELDS = ["ticker", "trading_date", "close_price", "adjusted_close", "volume", "source"]
SOURCE = "yfinance_history_backfill"
MINIMUM_ROWS = 250


def registered_tickers(path: Path = REGISTRY_PATH) -> set[str]:
    """Enabled vehicles in the registry (the reserve included, since it is also collected)."""
    registry = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        str(row["ticker"]).strip().upper()
        for row in registry.get("vehicles", [])
        if row.get("enabled", True)
    }


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _yfinance_frame(ticker: str, period: str):
    import yfinance as yf

    return yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)


def history_rows(ticker: str, period: str, fetch: Callable = _yfinance_frame) -> list[dict[str, object]]:
    frame = fetch(ticker, period)
    rows: list[dict[str, object]] = []
    for index, record in frame.iterrows():
        close = _number(record.get("Close"))
        if close is None or close <= 0:
            continue
        adjusted = _number(record.get("Adj Close"))
        volume = _number(record.get("Volume"))
        rows.append(
            {
                "ticker": ticker,
                "trading_date": index.date().isoformat(),
                "close_price": close,
                "adjusted_close": "" if adjusted is None else adjusted,
                "volume": "" if volume is None else volume,
                "source": SOURCE,
            }
        )
    return rows


def write_rows(path: Path, rows: Iterable[dict[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def main(argv: list[str] | None = None, fetch: Callable = _yfinance_frame) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tickers", required=True, help="Comma-separated registered tickers, e.g. GLDM")
    parser.add_argument("--period", default="3y", help="yfinance history period (default 3y)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    args = parser.parse_args(argv)

    requested = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    if not requested:
        raise SystemExit("no tickers requested")
    unknown = sorted(set(requested) - registered_tickers(args.registry))
    if unknown:
        raise SystemExit(f"not enabled in config/metals/vehicles.json: {unknown}")

    all_rows: list[dict[str, object]] = []
    for ticker in requested:
        rows = history_rows(ticker, args.period, fetch)
        if len(rows) < MINIMUM_ROWS:
            raise SystemExit(f"{ticker}: only {len(rows)} daily rows (need at least {MINIMUM_ROWS})")
        print(f"{ticker}: {len(rows)} rows {rows[0]['trading_date']} .. {rows[-1]['trading_date']}")
        all_rows.extend(rows)
    written = write_rows(args.output, all_rows)
    print(f"METALS VEHICLE HISTORY BACKFILL: {written} rows -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
