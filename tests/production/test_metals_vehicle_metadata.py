from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import pytest

from foundation.production.metals_vehicle_metadata import (
    MetalsVehicleMetadataError,
    assess_vehicle_metadata,
    build_vehicle_metadata_dataset,
    load_market_metadata,
    load_structural_metadata,
    summarize_vehicle_metadata,
)


def _structural(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "platform_id": "metals",
                "vehicles": [
                    {
                        "ticker": "TEST",
                        "issuer": "Issuer",
                        "legal_structure": "exchange_traded_fund",
                        "exposure_type": "physical_gold_bullion",
                        "exposure_share_pct": 100.0,
                        "concentration_description": "Single commodity",
                        "tax_structure": "grantor_trust",
                        "investability_classification": "directly_investable",
                        "metadata_source_url": "https://example.com/test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _market(path: Path, *, observed: str = "2026-07-01") -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "ticker",
                "expense_ratio_pct",
                "assets_under_management_usd",
                "average_daily_volume_shares",
                "median_bid_ask_spread_pct",
                "metadata_as_of_date",
                "source_name",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "ticker": "TEST",
                "expense_ratio_pct": "0.20",
                "assets_under_management_usd": "1000000000",
                "average_daily_volume_shares": "100000",
                "median_bid_ask_spread_pct": "0.05",
                "metadata_as_of_date": observed,
                "source_name": "Official source",
                "source_url": "https://example.com/test",
            }
        )
    return path


def test_complete_current_metadata_is_eligible(tmp_path: Path) -> None:
    structural = load_structural_metadata(_structural(tmp_path / "structural.json"))
    market = load_market_metadata(_market(tmp_path / "market.csv"))
    rows = build_vehicle_metadata_dataset(structural, market, as_of=date(2026, 7, 25))
    summary = summarize_vehicle_metadata(rows)

    assert rows[0]["completeness_status"] == "COMPLETE"
    assert rows[0]["freshness_status"] == "CURRENT"
    assert rows[0]["eligible_for_selection"] is True
    assert summary["status"] == "PASS"


def test_missing_market_metadata_is_incomplete(tmp_path: Path) -> None:
    structural = load_structural_metadata(_structural(tmp_path / "structural.json"))
    rows = build_vehicle_metadata_dataset(structural, {}, as_of=date(2026, 7, 25))

    assert rows[0]["completeness_status"] == "INCOMPLETE"
    assert rows[0]["freshness_status"] == "MISSING"
    assert rows[0]["eligible_for_selection"] is False
    assert "assets_under_management_usd" in rows[0]["missing_fields"]


def test_stale_metadata_is_not_eligible(tmp_path: Path) -> None:
    structural = load_structural_metadata(_structural(tmp_path / "structural.json"))
    market = load_market_metadata(_market(tmp_path / "market.csv", observed="2025-12-31"))
    rows = build_vehicle_metadata_dataset(structural, market, as_of=date(2026, 7, 25))

    assert rows[0]["completeness_status"] == "COMPLETE"
    assert rows[0]["freshness_status"] == "STALE"
    assert rows[0]["eligible_for_selection"] is False


def test_invalid_classification_fails_closed(tmp_path: Path) -> None:
    path = _structural(tmp_path / "structural.json")
    document = json.loads(path.read_text(encoding="utf-8"))
    document["vehicles"][0]["investability_classification"] = "unknown"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(MetalsVehicleMetadataError):
        load_structural_metadata(path)
