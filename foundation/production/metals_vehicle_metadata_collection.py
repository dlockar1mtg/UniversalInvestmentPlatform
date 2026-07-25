"""Collect dated Metals vehicle metadata from issuer-approved and market-data sources."""

from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Callable, Mapping


ISSUER_EXPENSE_RATIOS: dict[str, float] = {
    "BIL": 0.1353,
    "COPX": 0.65,
    "CPER": 1.06,
    "GLD": 0.40,
    "IAU": 0.25,
    "PPLT": 0.60,
    "SGOL": 0.17,
    "SIVR": 0.30,
    "SLV": 0.50,
    "URA": 0.69,
    "URNM": 0.75,
}

# Issuer-published 30-day median bid/ask spreads used only when the market-data
# provider does not return a usable spread or bid/ask pair. Values remain dated
# by the collection run and retain the issuer URL from the source template.
ISSUER_MEDIAN_BID_ASK_SPREAD_PCT: dict[str, float] = {
    "BIL": 0.01,
}


@dataclass(frozen=True)
class CollectedVehicleMetadata:
    ticker: str
    expense_ratio_pct: float | None
    assets_under_management_usd: float | None
    average_daily_volume_shares: float | None
    median_bid_ask_spread_pct: float | None
    metadata_as_of_date: str
    source_name: str
    source_url: str


def _positive(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _spread_pct(bid: object, ask: object) -> float | None:
    bid_value = _positive(bid)
    ask_value = _positive(ask)
    if bid_value is None or ask_value is None or ask_value < bid_value:
        return None
    midpoint = (bid_value + ask_value) / 2.0
    if midpoint <= 0:
        return None
    return round((ask_value - bid_value) / midpoint * 100.0, 6)


def collect_vehicle_metadata(
    *,
    template_path: Path,
    quote_loader: Callable[[str], Mapping[str, object]],
    as_of: date,
) -> list[CollectedVehicleMetadata]:
    with template_path.open(newline="", encoding="utf-8") as handle:
        template_rows = list(csv.DictReader(handle))

    results: list[CollectedVehicleMetadata] = []
    for row in template_rows:
        ticker = row["ticker"].strip().upper()
        quote = quote_loader(ticker)
        aum = _positive(quote.get("totalAssets") or quote.get("marketCap"))
        volume = _positive(
            quote.get("averageVolume")
            or quote.get("averageDailyVolume10Day")
            or quote.get("threeMonthAverageVolume")
        )
        spread = _positive(quote.get("medianBidAskSpreadPct"))
        spread_source = "Yahoo Finance market data"
        if spread is None:
            spread = _spread_pct(quote.get("bid"), quote.get("ask"))
        if spread is None:
            spread = ISSUER_MEDIAN_BID_ASK_SPREAD_PCT.get(ticker)
            if spread is not None:
                spread_source = "issuer-published 30-day median bid/ask spread"

        source_name = f"issuer expense ratio + {spread_source}"
        if aum is not None or volume is not None:
            source_name += " + Yahoo Finance market data"

        results.append(
            CollectedVehicleMetadata(
                ticker=ticker,
                expense_ratio_pct=ISSUER_EXPENSE_RATIOS.get(ticker),
                assets_under_management_usd=aum,
                average_daily_volume_shares=volume,
                median_bid_ask_spread_pct=spread,
                metadata_as_of_date=as_of.isoformat(),
                source_name=source_name,
                source_url=row["source_url"].strip(),
            )
        )
    return results


def write_collected_metadata(rows: list[CollectedVehicleMetadata], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else [
        "ticker",
        "expense_ratio_pct",
        "assets_under_management_usd",
        "average_daily_volume_shares",
        "median_bid_ask_spread_pct",
        "metadata_as_of_date",
        "source_name",
        "source_url",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
