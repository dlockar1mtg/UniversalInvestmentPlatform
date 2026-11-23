from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from foundation.production.metals_vehicle_metadata_collection import (
    collect_vehicle_metadata,
    write_collected_metadata,
)


def _template(path: Path, ticker: str = "GLD") -> Path:
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
        writer.writerow([ticker, "", "", "", "", "", "", f"https://issuer.example/{ticker.lower()}"])
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


def test_collection_uses_issuer_spread_fallback_for_bil(tmp_path: Path) -> None:
    rows = collect_vehicle_metadata(
        template_path=_template(tmp_path / "template.csv", ticker="BIL"),
        quote_loader=lambda ticker: {
            "totalAssets": 47_054_600_000,
            "averageVolume": 9_901_829,
            "bid": None,
            "ask": None,
        },
        as_of=date(2026, 7, 25),
    )

    row = rows[0]
    assert row.expense_ratio_pct == 0.1353
    assert row.median_bid_ask_spread_pct == 0.01
    assert "issuer-published 30-day median bid/ask spread" in row.source_name


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


def _last_good(path: Path, rows: list[tuple[str, str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "expense_ratio_pct", "assets_under_management_usd", "average_daily_volume_shares",
                         "median_bid_ask_spread_pct", "metadata_as_of_date", "source_name", "source_url"])
        for ticker, as_of in rows:
            writer.writerow([ticker, "0.4", "5000000", "100000", "0.02", as_of, "earlier run", f"https://issuer.example/{ticker.lower()}"])
    return path


def test_incomplete_fund_keeps_its_last_good_row(tmp_path: Path) -> None:
    from foundation.production.metals_vehicle_metadata_collection import carry_forward_incomplete

    fresh = collect_vehicle_metadata(
        template_path=_template(tmp_path / "template.csv"),
        quote_loader=lambda ticker: {},  # Yahoo sent nothing usable for this fund
        as_of=date(2026, 11, 19),
    )
    merged, carried = carry_forward_incomplete(
        fresh, last_good_path=_last_good(tmp_path / "good.csv", [("GLD", "2026-11-18")]), as_of=date(2026, 11, 19)
    )
    assert carried == ["GLD"]
    assert merged[0].assets_under_management_usd == 5_000_000
    assert merged[0].metadata_as_of_date == "2026-11-18"  # keeps its own date, so freshness still applies


def test_last_good_row_past_the_stale_line_is_not_carried(tmp_path: Path) -> None:
    from foundation.production.metals_vehicle_metadata_collection import carry_forward_incomplete

    fresh = collect_vehicle_metadata(
        template_path=_template(tmp_path / "template.csv"), quote_loader=lambda ticker: {}, as_of=date(2026, 11, 19)
    )
    merged, carried = carry_forward_incomplete(
        fresh, last_good_path=_last_good(tmp_path / "good.csv", [("GLD", "2026-07-25")]), as_of=date(2026, 11, 19)
    )
    assert carried == [] and merged[0].assets_under_management_usd is None


def test_complete_fresh_rows_are_never_replaced(tmp_path: Path) -> None:
    from foundation.production.metals_vehicle_metadata_collection import carry_forward_incomplete

    fresh = collect_vehicle_metadata(
        template_path=_template(tmp_path / "template.csv"),
        quote_loader=lambda ticker: {"totalAssets": 9_000_000, "averageVolume": 1, "bid": 99.9, "ask": 100.1},
        as_of=date(2026, 11, 19),
    )
    merged, carried = carry_forward_incomplete(
        fresh, last_good_path=_last_good(tmp_path / "good.csv", [("GLD", "2026-11-18")]), as_of=date(2026, 11, 19)
    )
    assert carried == [] and merged[0].assets_under_management_usd == 9_000_000


def test_missing_last_good_file_changes_nothing(tmp_path: Path) -> None:
    from foundation.production.metals_vehicle_metadata_collection import carry_forward_incomplete

    fresh = collect_vehicle_metadata(
        template_path=_template(tmp_path / "template.csv"), quote_loader=lambda ticker: {}, as_of=date(2026, 11, 19)
    )
    assert carry_forward_incomplete(fresh, last_good_path=tmp_path / "none.csv", as_of=date(2026, 11, 19))[1] == []


def test_retry_fills_a_fund_yahoo_skipped_the_first_time(tmp_path: Path) -> None:
    from foundation.production.metals_vehicle_metadata_collection import retry_incomplete

    template = _template(tmp_path / "template.csv")
    calls = {"n": 0}

    def flaky(ticker):
        calls["n"] += 1
        return {} if calls["n"] == 1 else {"totalAssets": 7_000_000, "averageVolume": 10, "bid": 99.9, "ask": 100.1}

    first = collect_vehicle_metadata(template_path=template, quote_loader=flaky, as_of=date(2026, 11, 19))
    pauses = []
    fixed = retry_incomplete(first, template_path=template, quote_loader=flaky, as_of=date(2026, 11, 19), sleep=pauses.append)
    assert fixed[0].assets_under_management_usd == 7_000_000 and pauses == [10.0]


def test_retry_gives_up_after_the_set_attempts(tmp_path: Path) -> None:
    from foundation.production.metals_vehicle_metadata_collection import retry_incomplete

    template = _template(tmp_path / "template.csv")
    first = collect_vehicle_metadata(template_path=template, quote_loader=lambda t: {}, as_of=date(2026, 11, 19))
    pauses = []
    out = retry_incomplete(first, template_path=template, quote_loader=lambda t: {}, as_of=date(2026, 11, 19), sleep=pauses.append)
    assert out[0].assets_under_management_usd is None and len(pauses) == 2
