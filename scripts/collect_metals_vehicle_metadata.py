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
    carry_forward_incomplete,
    retry_incomplete,
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
    # Each source on its own: one failing part of Yahoo (often the quoteSummary "info" call) must not
    # throw away what the others returned.
    info: dict[str, object] = {}
    try:
        info = dict(security.info or {})
    except Exception as exc:  # noqa: BLE001 - recorded, other sources still tried
        print(f"{ticker}: Yahoo info unavailable ({type(exc).__name__})")
    fast: dict[str, object] = {}
    try:
        fast_info = security.fast_info
        for key in ("marketCap", "threeMonthAverageVolume", "tenDayAverageVolume", "lastPrice"):
            try:
                value = fast_info[key]
            except Exception:  # noqa: BLE001
                continue
            if value is not None:
                fast[key] = value
    except Exception as exc:  # noqa: BLE001
        print(f"{ticker}: Yahoo fast_info unavailable ({type(exc).__name__})")
    combined = {**fast, **{k: v for k, v in info.items() if v is not None}}
    if not any(combined.get(k) for k in ("averageVolume", "averageDailyVolume10Day", "threeMonthAverageVolume")):
        try:   # the daily price history (chart API) is Yahoo's sturdiest endpoint
            volume = security.history(period="3mo", interval="1d", auto_adjust=False)["Volume"].dropna()
            if len(volume) >= 20:
                combined["threeMonthAverageVolume"] = float(volume.tail(63).mean())
        except Exception as exc:  # noqa: BLE001
            print(f"{ticker}: Yahoo price history unavailable ({type(exc).__name__})")
    missing = [k for k in ("totalAssets/marketCap", "averageVolume") if
               not (combined.get("totalAssets") or combined.get("marketCap")) and k.startswith("total")
               or not any(combined.get(x) for x in ("averageVolume", "averageDailyVolume10Day",
                                                     "threeMonthAverageVolume")) and k == "averageVolume"]
    if missing:
        print(f"{ticker}: Yahoo did not return {', '.join(missing)}")
    return combined


def main() -> int:
    args = parse_arguments()
    rows = collect_vehicle_metadata(
        template_path=args.template,
        quote_loader=_yahoo_quote_loader,
        as_of=args.as_of,
    )
    # Yahoo's gaps are usually momentary: ask again for just the incomplete funds before carrying.
    rows = retry_incomplete(rows, template_path=args.template, quote_loader=_yahoo_quote_loader, as_of=args.as_of)
    # What Yahoo left out is filled field by field from the fund's last good row (the template, which the
    # workflow refreshes from the last good run) while that row is within 180 days.
    rows, carried = carry_forward_incomplete(rows, last_good_path=args.template, as_of=args.as_of)
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
        "carried_from_last_good": carried,
        "output": str(args.output.resolve()),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    print()
    print("METALS VEHICLE METADATA COLLECTION: COMPLETE" if complete == len(rows) else "METALS VEHICLE METADATA COLLECTION: PARTIAL")
    return 0 if complete == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
