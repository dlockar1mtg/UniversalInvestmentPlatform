from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BENCHMARKS = {
    "BIL": "^IRX",
    "COPX": "HG=F",
    "CPER": "HG=F",
    "GLD": "GC=F",
    "IAU": "GC=F",
    "PPLT": "PL=F",
    "SGOL": "GC=F",
    "SIVR": "SI=F",
    "SLV": "SI=F",
    "URA": "URA",
    "URNM": "URA",
}


def _history_pair(ticker: str) -> tuple[str, float, float]:
    import yfinance as yf

    history = yf.Ticker(ticker).history(period="10d", interval="1d", auto_adjust=False)
    history = history.dropna(subset=["Close"])
    if len(history) < 2:
        raise RuntimeError(f"insufficient daily history for {ticker}")
    previous = float(history.iloc[-2]["Close"])
    current = float(history.iloc[-1]["Close"])
    trading_date = history.index[-1].date().isoformat()
    return trading_date, current, previous


def main() -> int:
    metadata_path = ROOT / "config" / "metals" / "vehicle_market_metadata.csv"
    output_path = ROOT / "data" / "operations" / "metals" / "daily_market_input.csv"
    with metadata_path.open(newline="", encoding="utf-8") as handle:
        metadata_rows = list(csv.DictReader(handle))

    output_rows: list[dict[str, object]] = []
    for row in metadata_rows:
        ticker = row["ticker"].strip().upper()
        benchmark = BENCHMARKS[ticker]
        trading_date, close_price, previous_close_price = _history_pair(ticker)
        _, benchmark_close, benchmark_previous = _history_pair(benchmark)
        output_rows.append({
            "ticker": ticker,
            "trading_date": trading_date,
            "close_price": close_price,
            "previous_close_price": previous_close_price,
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
