"""Fetch month-end crypto closes from Kraken and merge them into the stored history.

Kraken's public weekly OHLC returns the last 720 weeks per pair, so the stored file (not Kraken)
is the long-term record: each run updates recent months and keeps every older month already stored.
A month's close is the close of its last weekly candle; the current month's close is the latest price.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "crypto" / "crypto_monthly_closes.csv"
PAIRS = {"bitcoin": "XBTUSD", "ethereum": "ETHUSD", "solana": "SOLUSD", "chainlink": "LINKUSD", "xrp": "XRPUSD", "avalanche": "AVAXUSD"}
URL = "https://api.kraken.com/0/public/OHLC?pair={pair}&interval=10080"
FIELDS = ["asset", "month", "close", "source", "updated_utc"]


def _fetch(url: str):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "uip-crypto-v2"}), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def month_closes(payload) -> dict[str, float]:
    if payload.get("error"):
        raise RuntimeError(f"Kraken error: {payload['error']}")
    result = payload.get("result") or {}
    key = next((k for k in result if k != "last"), None)
    closes = {}
    for candle in result.get(key, []) if key else []:
        month = datetime.fromtimestamp(int(candle[0]), tz=timezone.utc).strftime("%Y-%m")
        closes[month] = float(candle[4])          # candles arrive in time order: the last one in a month wins
    return closes


def merge(existing: list[dict], fresh: dict[str, dict[str, float]], stamp: str) -> list[dict]:
    rows = {(r["asset"], r["month"]): r for r in existing}
    for asset, closes in fresh.items():
        for month, close in closes.items():
            rows[(asset, month)] = {"asset": asset, "month": month, "close": f"{close:.8g}", "source": "KRAKEN_WEEKLY_OHLC", "updated_utc": stamp}
    return sorted(rows.values(), key=lambda r: (r["asset"], r["month"]))


def main(argv=None, fetch=_fetch, now=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--sleep-seconds", type=float, default=1.5)
    args = parser.parse_args(argv)
    existing = []
    if args.output.is_file():
        with args.output.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    fresh, failures = {}, []
    for asset, pair in PAIRS.items():
        try:
            fresh[asset] = month_closes(fetch(URL.format(pair=pair)))
        except Exception as exc:  # noqa: BLE001 - one pair failing keeps the others
            failures.append(f"{asset}: {type(exc).__name__}")
        time.sleep(args.sleep_seconds)
    if not fresh:
        raise SystemExit(f"no crypto prices fetched ({'; '.join(failures)})")
    core_failed = [a for a in ("bitcoin", "ethereum") if a not in fresh]
    if core_failed:
        # The calls are made for these two: fail visibly rather than commit a file where they silently lag.
        raise SystemExit(f"core crypto prices not fetched: {', '.join(core_failed)} ({'; '.join(failures)})")
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = merge(existing, fresh, stamp)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(fresh)} of {len(PAIRS)} assets updated; {len(rows)} month rows stored; failures: {failures or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
