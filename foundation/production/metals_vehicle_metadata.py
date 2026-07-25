"""Vehicle metadata contracts, completeness validation, and dashboard projections."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


STRUCTURAL_REQUIRED = (
    "issuer",
    "legal_structure",
    "exposure_type",
    "tax_structure",
    "investability_classification",
)
MARKET_REQUIRED = (
    "expense_ratio_pct",
    "assets_under_management_usd",
    "average_daily_volume_shares",
    "median_bid_ask_spread_pct",
    "metadata_as_of_date",
)
VALID_INVESTABILITY = {
    "directly_investable",
    "diversified_fund_only",
    "futures_only",
    "research_only",
    "no_approved_vehicle",
}
VALID_FRESHNESS = {"CURRENT", "AGING", "STALE", "MISSING"}


class MetalsVehicleMetadataError(ValueError):
    """Raised when vehicle metadata violates the Phase 8.9.4 contract."""


@dataclass(frozen=True)
class VehicleStructuralMetadata:
    ticker: str
    issuer: str
    legal_structure: str
    exposure_type: str
    exposure_share_pct: float | None
    concentration_description: str
    tax_structure: str
    investability_classification: str
    metadata_source_url: str


@dataclass(frozen=True)
class VehicleMarketMetadata:
    ticker: str
    expense_ratio_pct: float | None
    assets_under_management_usd: float | None
    average_daily_volume_shares: float | None
    median_bid_ask_spread_pct: float | None
    metadata_as_of_date: str | None
    source_name: str
    source_url: str


@dataclass(frozen=True)
class VehicleMetadataAssessment:
    ticker: str
    completeness_status: str
    freshness_status: str
    missing_fields: tuple[str, ...]
    metadata_age_days: int | None
    investability_classification: str
    eligible_for_selection: bool


def _read_json(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MetalsVehicleMetadataError(f"cannot read metadata file: {path}") from exc
    if not isinstance(document, dict):
        raise MetalsVehicleMetadataError(f"metadata file must contain an object: {path}")
    return document


def load_structural_metadata(path: str | Path) -> dict[str, VehicleStructuralMetadata]:
    document = _read_json(Path(path))
    if document.get("schema_version") != "1.0" or document.get("platform_id") != "metals":
        raise MetalsVehicleMetadataError("invalid structural metadata header")
    try:
        records = [VehicleStructuralMetadata(**item) for item in document["vehicles"]]
    except (KeyError, TypeError) as exc:
        raise MetalsVehicleMetadataError("structural metadata does not match schema") from exc
    output = {record.ticker: record for record in records}
    if len(output) != len(records):
        raise MetalsVehicleMetadataError("duplicate ticker in structural metadata")
    for record in records:
        if record.ticker != record.ticker.upper():
            raise MetalsVehicleMetadataError(f"ticker must be uppercase: {record.ticker}")
        if record.investability_classification not in VALID_INVESTABILITY:
            raise MetalsVehicleMetadataError(f"invalid investability classification: {record.ticker}")
        if not record.metadata_source_url.startswith("https://"):
            raise MetalsVehicleMetadataError(f"metadata source must use HTTPS: {record.ticker}")
        if record.exposure_share_pct is not None and not 0 <= record.exposure_share_pct <= 100:
            raise MetalsVehicleMetadataError(f"invalid exposure share: {record.ticker}")
    return output


def load_market_metadata(path: str | Path) -> dict[str, VehicleMarketMetadata]:
    selected = Path(path)
    if not selected.exists():
        return {}
    with selected.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        records = []
        for row in reader:
            def number(name: str) -> float | None:
                value = (row.get(name) or "").strip()
                return None if not value else float(value)

            records.append(
                VehicleMarketMetadata(
                    ticker=(row.get("ticker") or "").strip().upper(),
                    expense_ratio_pct=number("expense_ratio_pct"),
                    assets_under_management_usd=number("assets_under_management_usd"),
                    average_daily_volume_shares=number("average_daily_volume_shares"),
                    median_bid_ask_spread_pct=number("median_bid_ask_spread_pct"),
                    metadata_as_of_date=(row.get("metadata_as_of_date") or "").strip() or None,
                    source_name=(row.get("source_name") or "").strip(),
                    source_url=(row.get("source_url") or "").strip(),
                )
            )
    output = {record.ticker: record for record in records}
    if len(output) != len(records):
        raise MetalsVehicleMetadataError("duplicate ticker in market metadata")
    for record in records:
        if not record.ticker:
            raise MetalsVehicleMetadataError("market metadata ticker is required")
        if record.source_url and not record.source_url.startswith("https://"):
            raise MetalsVehicleMetadataError(f"market metadata source must use HTTPS: {record.ticker}")
        for field_name in (
            "expense_ratio_pct",
            "assets_under_management_usd",
            "average_daily_volume_shares",
            "median_bid_ask_spread_pct",
        ):
            value = getattr(record, field_name)
            if value is not None and value < 0:
                raise MetalsVehicleMetadataError(f"negative {field_name}: {record.ticker}")
    return output


def freshness_status(
    metadata_as_of_date: str | None,
    *,
    as_of: date,
    current_days: int = 45,
    aging_days: int = 90,
) -> tuple[str, int | None]:
    if not metadata_as_of_date:
        return "MISSING", None
    observed = date.fromisoformat(metadata_as_of_date)
    age = (as_of - observed).days
    if age < 0:
        raise MetalsVehicleMetadataError("metadata as-of date cannot be in the future")
    if age <= current_days:
        return "CURRENT", age
    if age <= aging_days:
        return "AGING", age
    return "STALE", age


def assess_vehicle_metadata(
    structural: VehicleStructuralMetadata,
    market: VehicleMarketMetadata | None,
    *,
    as_of: date,
) -> VehicleMetadataAssessment:
    missing = [field for field in STRUCTURAL_REQUIRED if not getattr(structural, field)]
    if market is None:
        missing.extend(MARKET_REQUIRED)
        freshness, age = "MISSING", None
    else:
        missing.extend(field for field in MARKET_REQUIRED if getattr(market, field) in (None, ""))
        freshness, age = freshness_status(market.metadata_as_of_date, as_of=as_of)
    completeness = "COMPLETE" if not missing else "INCOMPLETE"
    eligible = (
        completeness == "COMPLETE"
        and freshness in {"CURRENT", "AGING"}
        and structural.investability_classification
        in {"directly_investable", "diversified_fund_only", "futures_only"}
    )
    return VehicleMetadataAssessment(
        ticker=structural.ticker,
        completeness_status=completeness,
        freshness_status=freshness,
        missing_fields=tuple(sorted(set(missing))),
        metadata_age_days=age,
        investability_classification=structural.investability_classification,
        eligible_for_selection=eligible,
    )


def build_vehicle_metadata_dataset(
    structural_records: dict[str, VehicleStructuralMetadata],
    market_records: dict[str, VehicleMarketMetadata],
    *,
    as_of: date,
) -> list[dict]:
    rows: list[dict] = []
    for ticker in sorted(structural_records):
        structural = structural_records[ticker]
        market = market_records.get(ticker)
        assessment = assess_vehicle_metadata(structural, market, as_of=as_of)
        row = asdict(structural)
        if market:
            row.update(asdict(market))
        else:
            row.update({field: None for field in MARKET_REQUIRED})
            row.update({"source_name": "", "source_url": ""})
        row.update(asdict(assessment))
        row["missing_fields"] = "|".join(assessment.missing_fields)
        rows.append(row)
    return rows


def summarize_vehicle_metadata(rows: Iterable[dict], *, generated_at: datetime | None = None) -> dict:
    materialized = list(rows)
    generated = generated_at or datetime.now(timezone.utc)
    complete = sum(row["completeness_status"] == "COMPLETE" for row in materialized)
    eligible = sum(bool(row["eligible_for_selection"]) for row in materialized)
    freshness_counts = {
        status: sum(row["freshness_status"] == status for row in materialized)
        for status in sorted(VALID_FRESHNESS)
    }
    return {
        "generated_at_utc": generated.astimezone(timezone.utc).isoformat(),
        "vehicle_count": len(materialized),
        "complete_vehicle_count": complete,
        "incomplete_vehicle_count": len(materialized) - complete,
        "eligible_vehicle_count": eligible,
        "freshness_counts": freshness_counts,
        "status": "PASS" if materialized and complete == len(materialized) else "INCOMPLETE",
    }


def write_vehicle_metadata_outputs(rows: list[dict], summary: dict, output_root: str | Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "vehicle_metadata_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "vehicle_metadata.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if rows:
        with (root / "vehicle_metadata.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
