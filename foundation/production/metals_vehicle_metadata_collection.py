"""Collect dated Metals vehicle metadata from issuer-approved and market-data sources."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Callable, Mapping


_COST_EVIDENCE_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "presentation" / "metals_vehicle_cost_evidence_snapshot_v1.json"
)
# BIL is the cash reserve, not an implementation vehicle, so it is not in the cost evidence.
_RESERVE_EXPENSE_RATIOS: dict[str, float] = {"BIL": 0.1353}


def _issuer_expense_ratios() -> dict[str, float]:
    """Issuer expense ratios from the dated cost evidence, the single source for fees."""
    evidence = json.loads(_COST_EVIDENCE_PATH.read_text(encoding="utf-8-sig"))
    ratios = dict(_RESERVE_EXPENSE_RATIOS)
    for row in evidence.get("vehicles", []):
        ratios[str(row["ticker"]).upper()] = float(row["expense_ratio_pct"])
    return ratios


ISSUER_EXPENSE_RATIOS: dict[str, float] = _issuer_expense_ratios()

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


def _is_complete(row: CollectedVehicleMetadata) -> bool:
    return (
        row.expense_ratio_pct is not None
        and row.assets_under_management_usd is not None
        and row.average_daily_volume_shares is not None
        and row.median_bid_ask_spread_pct is not None
    )


def _float_or_none(value: object) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def carry_forward_incomplete(
    rows: list[CollectedVehicleMetadata],
    *,
    last_good_path: Path,
    as_of: date,
    max_age_days: int = 90,
) -> tuple[list[CollectedVehicleMetadata], list[str]]:
    """Keep a fund's last good row when today's market-data reply for it is incomplete.

    Yahoo often answers for 11 of 12 funds. Rather than failing every fund, the incomplete one keeps
    its previous complete row with its own (older) as-of date, so the freshness rules still judge it.
    A previous row older than ``max_age_days`` (the STALE line) is not carried. Returns the rows and
    the carried tickers.
    """
    previous: dict[str, CollectedVehicleMetadata] = {}
    if last_good_path.is_file():
        with last_good_path.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                as_of_text = (raw.get("metadata_as_of_date") or "").strip()
                if not as_of_text:
                    continue
                try:
                    observed = date.fromisoformat(as_of_text)
                except ValueError:
                    continue
                if not 0 <= (as_of - observed).days <= max_age_days:
                    continue
                candidate = CollectedVehicleMetadata(
                    ticker=raw["ticker"].strip().upper(),
                    expense_ratio_pct=_float_or_none(raw.get("expense_ratio_pct")),
                    assets_under_management_usd=_float_or_none(raw.get("assets_under_management_usd")),
                    average_daily_volume_shares=_float_or_none(raw.get("average_daily_volume_shares")),
                    median_bid_ask_spread_pct=_float_or_none(raw.get("median_bid_ask_spread_pct")),
                    metadata_as_of_date=as_of_text,
                    source_name=(raw.get("source_name") or "").strip(),
                    source_url=(raw.get("source_url") or "").strip(),
                )
                if _is_complete(candidate):
                    previous[candidate.ticker] = candidate
    merged: list[CollectedVehicleMetadata] = []
    carried: list[str] = []
    for row in rows:
        if not _is_complete(row) and row.ticker in previous:
            merged.append(previous[row.ticker])
            carried.append(row.ticker)
        else:
            merged.append(row)
    return merged, carried


def retry_incomplete(
    rows: list[CollectedVehicleMetadata],
    *,
    template_path: Path,
    quote_loader: Callable[[str], Mapping[str, object]],
    as_of: date,
    attempts: int = 2,
    pause_seconds: float = 10.0,
    sleep: Callable[[float], None] | None = None,
) -> list[CollectedVehicleMetadata]:
    """Ask the market-data source again for funds whose reply was incomplete, keeping the order."""
    import tempfile
    import time

    sleep = sleep or time.sleep
    with template_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        template_rows = {row["ticker"].strip().upper(): row for row in reader}
    current = {row.ticker: row for row in rows}
    for _ in range(attempts):
        missing = [ticker for ticker, row in current.items() if not _is_complete(row)]
        if not missing:
            break
        sleep(pause_seconds)
        with tempfile.TemporaryDirectory() as folder:
            subset = Path(folder) / "retry.csv"
            with subset.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for ticker in missing:
                    writer.writerow(template_rows[ticker])
            for row in collect_vehicle_metadata(template_path=subset, quote_loader=quote_loader, as_of=as_of):
                if _is_complete(row):
                    current[row.ticker] = row
    return [current[row.ticker] for row in rows]
