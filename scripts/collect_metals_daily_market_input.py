from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _registered_benchmarks() -> dict[str, str]:
    """Each vehicle's tracking benchmark symbol from config/metals/vehicles.json."""
    registry = json.loads((ROOT / "config" / "metals" / "vehicles.json").read_text(encoding="utf-8-sig"))
    return {
        str(row["ticker"]).strip().upper(): str(row["benchmark_symbol"])
        for row in registry.get("vehicles", [])
        if row.get("benchmark_symbol")
    }


BENCHMARKS = _registered_benchmarks()


def _history_pair(ticker: str) -> tuple[str, float, float, float | None]:
    import yfinance as yf

    history = yf.Ticker(ticker).history(period="10d", interval="1d", auto_adjust=False)
    history = history.dropna(subset=["Close"])
    if len(history) < 2:
        raise RuntimeError(f"insufficient daily history for {ticker}")
    previous = float(history.iloc[-2]["Close"])
    current = float(history.iloc[-1]["Close"])
    trading_date = history.index[-1].date().isoformat()
    # The session's real traded volume (the metadata ADV snapshot is a fixed July figure).
    try:
        volume = float(history.iloc[-1]["Volume"])
    except (KeyError, TypeError, ValueError):
        volume = None
    if volume is not None and (volume != volume or volume < 0):
        volume = None
    return trading_date, current, previous, volume


def main() -> int:
    metadata_path = ROOT / "config" / "metals" / "vehicle_market_metadata.csv"
    output_path = ROOT / "data" / "operations" / "metals" / "daily_market_input.csv"
    with metadata_path.open(newline="", encoding="utf-8") as handle:
        metadata_rows = list(csv.DictReader(handle))

    output_rows: list[dict[str, object]] = []
    for row in metadata_rows:
        ticker = row["ticker"].strip().upper()
        benchmark = BENCHMARKS.get(ticker)
        if benchmark is None:
            raise RuntimeError(f"No benchmark_symbol registered for {ticker} in config/metals/vehicles.json")
        trading_date, close_price, previous_close_price, volume = _history_pair(ticker)
        _, benchmark_close, benchmark_previous, _ = _history_pair(benchmark)
        output_rows.append({
            "ticker": ticker,
            "trading_date": trading_date,
            "close_price": close_price,
            "previous_close_price": previous_close_price,
            "volume": "" if volume is None else volume,
            "benchmark_symbol": benchmark,
            "benchmark_close_price": benchmark_close,
            "benchmark_previous_close_price": benchmark_previous,
            "expense_ratio_pct": row["expense_ratio_pct"],
            "average_daily_volume_shares": row["average_daily_volume_shares"],
            "median_bid_ask_spread_pct": row["median_bid_ask_spread_pct"],
            "metadata_as_of_date": row["metadata_as_of_date"],
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(output_rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"METALS DAILY MARKET INPUT: COMPLETE")
    print(f"Vehicles: {len(output_rows)}")
    print(f"Collected on: {date.today().isoformat()}")
    print(f"Output: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
