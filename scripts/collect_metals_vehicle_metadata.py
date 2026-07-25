"""Collect current Metals vehicle metadata and publish the validation surface."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_vehicle_metadata_collection import (  # noqa: E402
    collect_vehicle_metadata,
    write_collected_metadata,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Metals vehicle metadata.")
    parser.add_argument(
        "--template",
        type=Path,
        default=ROOT / "config" / "metals" / "vehicle_market_metadata.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "config" / "metals" / "vehicle_market_metadata.csv",
    )
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    return parser.parse_args()


def _yahoo_quote_loader(ticker: str) -> dict[str, object]:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is required for vehicle metadata collection") from exc

    security = yf.Ticker(ticker)
    info = dict(security.info or {})
    try:
        fast = dict(security.fast_info or {})
    except Exception:
        fast = {}
    combined = {**fast, **info}
    return combined


def main() -> int:
    args = parse_arguments()
    rows = collect_vehicle_metadata(
        template_path=args.template,
        quote_loader=_yahoo_quote_loader,
        as_of=args.as_of,
    )
    write_collected_metadata(rows, args.output)

    complete = sum(
        1
        for row in rows
        if row.expense_ratio_pct is not None
        and row.assets_under_management_usd is not None
        and row.average_daily_volume_shares is not None
        and row.median_bid_ask_spread_pct is not None
    )
    payload = {
        "as_of": args.as_of.isoformat(),
        "vehicle_count": len(rows),
        "complete_collection_count": complete,
        "output": str(args.output.resolve()),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    print()
    print("METALS VEHICLE METADATA COLLECTION: COMPLETE" if complete == len(rows) else "METALS VEHICLE METADATA COLLECTION: PARTIAL")
    return 0 if complete == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
