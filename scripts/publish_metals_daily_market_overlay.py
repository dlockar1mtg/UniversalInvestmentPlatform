from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_daily_market_overlay import (  # noqa: E402
    DailyMarketObservation,
    build_daily_market_overlay,
    summarize_daily_market_overlay,
    write_daily_market_overlay_outputs,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish the Metals daily market overlay.")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data" / "operations" / "metals" / "daily_market_input.csv",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "data" / "operations" / "metals" / "daily_market_overlay",
    )
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def _load(path: Path) -> list[DailyMarketObservation]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        DailyMarketObservation(
            ticker=row["ticker"].strip().upper(),
            trading_date=row["trading_date"],
            close_price=float(row["close_price"]),
            previous_close_price=float(row["previous_close_price"]),
            benchmark_symbol=row["benchmark_symbol"].strip().upper(),
            benchmark_close_price=float(row["benchmark_close_price"]),
            benchmark_previous_close_price=float(row["benchmark_previous_close_price"]),
            expense_ratio_pct=float(row["expense_ratio_pct"]),
            average_daily_volume_shares=float(row["average_daily_volume_shares"]),
            median_bid_ask_spread_pct=float(row["median_bid_ask_spread_pct"]),
            metadata_as_of_date=row["metadata_as_of_date"],
        )
        for row in rows
    ]


def main() -> int:
    args = parse_arguments()
    observations = _load(args.input)
    rows = build_daily_market_overlay(observations, as_of=args.as_of)
    summary = summarize_daily_market_overlay(rows)
    write_daily_market_overlay_outputs(rows, summary, args.output_root)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print()
    print(f"METALS DAILY MARKET OVERLAY: {summary['status']}")
    print(f"Vehicles: {summary['vehicle_count']}")
    print(f"Current: {summary['current_vehicle_count']}")
    print(f"Alerts: {summary['alert_count']}")
    print(f"Highest severity: {summary['highest_alert_severity']}")
    print(f"Output: {args.output_root.resolve()}")
    if args.strict and summary["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
