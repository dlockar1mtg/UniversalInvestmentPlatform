from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from foundation.production.metals_vehicle_metadata_collection import (
    collect_vehicle_metadata,
    write_collected_metadata,
)


def _template(path: Path) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "ticker",
            "expense_ratio_pct",
            "assets_under_management_usd",
            "average_daily_volume_shares",
            "median_bid_ask_spread_pct",
            "metadata_as_of_date",
            "source_name",
            "source_url",
        ])
        writer.writerow(["GLD", "", "", "", "", "", "", "https://issuer.example/gld"])
    return path


def test_collection_combines_issuer_and_market_fields(tmp_path: Path) -> None:
    rows = collect_vehicle_metadata(
        template_path=_template(tmp_path / "template.csv"),
        quote_loader=lambda ticker: {
            "totalAssets": 10_000_000,
            "averageVolume": 500_000,
            "bid": 99.9,
            "ask": 100.1,
        },
        as_of=date(2026, 7, 25),
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.ticker == "GLD"
    assert row.expense_ratio_pct == 0.40
    assert row.assets_under_management_usd == 10_000_000
    assert row.average_daily_volume_shares == 500_000
    assert row.median_bid_ask_spread_pct == 0.2
    assert row.metadata_as_of_date == "2026-07-25"


def test_collection_preserves_missing_provider_values(tmp_path: Path) -> None:
    rows = collect_vehicle_metadata(
        template_path=_template(tmp_path / "template.csv"),
        quote_loader=lambda ticker: {},
        as_of=date(2026, 7, 25),
    )

    assert rows[0].assets_under_management_usd is None
    assert rows[0].average_daily_volume_shares is None
    assert rows[0].median_bid_ask_spread_pct is None


def test_write_collected_metadata_round_trips(tmp_path: Path) -> None:
    rows = collect_vehicle_metadata(
        template_path=_template(tmp_path / "template.csv"),
        quote_loader=lambda ticker: {
            "totalAssets": 10_000_000,
            "averageVolume": 500_000,
            "medianBidAskSpreadPct": 0.03,
        },
        as_of=date(2026, 7, 25),
    )
    output = tmp_path / "output.csv"
    write_collected_metadata(rows, output)

    with output.open(newline="", encoding="utf-8") as handle:
        document = list(csv.DictReader(handle))
    assert document[0]["ticker"] == "GLD"
    assert document[0]["median_bid_ask_spread_pct"] == "0.03"
