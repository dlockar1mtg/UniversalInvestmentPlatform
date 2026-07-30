from __future__ import annotations

import csv
from pathlib import Path

from scripts.validate_contracts import validate_csv


COLUMNS = [
    "contract_version",
    "platform_id",
    "run_id",
    "universal_asset_id",
    "performance_status",
    "performance_eligible",
    "historical_start_date",
    "historical_end_date",
    "historical_start_value",
    "historical_end_value",
    "elapsed_days",
    "observation_count",
    "distinct_date_count",
    "source_count",
    "historical_sources",
    "total_return_pct",
    "cagr_pct",
    "annualized_return_pct",
    "minimum_value",
    "maximum_value",
    "data_quality",
    "suppression_reason",
    "currency",
    "source_system",
    "model_version",
    "generated_at_utc",
    "notes",
    "metadata_json",
]


def _eligible_row() -> dict[str, object]:
    return {
        "contract_version": "1.0.0",
        "platform_id": "mtg",
        "run_id": "run-001",
        "universal_asset_id": "mtg:secret-lair-example",
        "performance_status": "eligible",
        "performance_eligible": True,
        "historical_start_date": "2021-07-16",
        "historical_end_date": "2026-07-16",
        "historical_start_value": 100,
        "historical_end_value": 165,
        "elapsed_days": 1826,
        "observation_count": 48,
        "distinct_date_count": 48,
        "source_count": 2,
        "historical_sources": "tcgplayer|mtgjson",
        "total_return_pct": 0.65,
        "cagr_pct": 0.1053,
        "annualized_return_pct": 0.1053,
        "minimum_value": 92,
        "maximum_value": 175,
        "data_quality": "high",
        "suppression_reason": "",
        "currency": "USD",
        "source_system": "mtg-investment-terminal",
        "model_version": "test",
        "generated_at_utc": "2026-07-16T18:06:30Z",
        "notes": "",
        "metadata_json": "{}",
    }


def _write_csv(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_eligible_historical_performance_is_valid(
    tmp_path: Path,
) -> None:
    path = tmp_path / "historical_performance.csv"
    _write_csv(path, [_eligible_row()])

    report = validate_csv(path, "historical_performance")

    assert report["valid"] is True
    assert report["errors"] == []


def test_suppressed_row_requires_reason(
    tmp_path: Path,
) -> None:
    row = _eligible_row()
    row.update({
        "performance_status": "insufficient_data",
        "performance_eligible": False,
        "historical_start_date": "",
        "historical_end_date": "",
        "historical_start_value": "",
        "historical_end_value": "",
        "elapsed_days": "",
        "observation_count": "",
        "distinct_date_count": "",
        "source_count": "",
        "suppression_reason": "",
        "data_quality": "insufficient",
    })

    path = tmp_path / "historical_performance.csv"
    _write_csv(path, [row])

    report = validate_csv(path, "historical_performance")

    assert report["valid"] is False
    assert any(
        "requires suppression_reason" in error
        for error in report["errors"]
    )


def test_eligible_row_requires_evidence(
    tmp_path: Path,
) -> None:
    row = _eligible_row()
    row["observation_count"] = ""

    path = tmp_path / "historical_performance.csv"
    _write_csv(path, [row])

    report = validate_csv(path, "historical_performance")

    assert report["valid"] is False
    assert any(
        "eligible historical performance requires" in error
        for error in report["errors"]
    )


def test_date_and_elapsed_days_must_reconcile(
    tmp_path: Path,
) -> None:
    row = _eligible_row()
    row["elapsed_days"] = 10

    path = tmp_path / "historical_performance.csv"
    _write_csv(path, [row])

    report = validate_csv(path, "historical_performance")

    assert report["valid"] is False
    assert any(
        "elapsed_days must equal" in error
        for error in report["errors"]
    )


def test_duplicate_asset_in_same_run_is_invalid(
    tmp_path: Path,
) -> None:
    row = _eligible_row()

    path = tmp_path / "historical_performance.csv"
    _write_csv(path, [row, row.copy()])

    report = validate_csv(path, "historical_performance")

    assert report["valid"] is False
    assert any(
        "Duplicate logical primary key" in error
        for error in report["errors"]
    )
