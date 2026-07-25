"""Industrial Metals vehicle-coverage contracts, validation, and publication."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping


REQUIRED_METALS = ("aluminum", "zinc", "nickel", "tin")
ALLOWED_COVERAGE_STATUSES = {
    "DIRECTLY_INVESTABLE",
    "FUND_ONLY",
    "FUTURES_ONLY",
    "RESEARCH_ONLY",
    "NO_APPROVED_VEHICLE",
}


@dataclass(frozen=True)
class IndustrialVehicleCoverageRow:
    metal_id: str
    benchmark_symbol: str | None
    coverage_status: str
    approved_vehicle_ticker: str | None
    candidate_vehicles: str
    candidate_structure: str | None
    candidate_exposure: str | None
    decision_reason: str
    selection_eligible: bool
    source_refs: str
    validation_status: str


def _join(values: object) -> str:
    if not isinstance(values, list):
        return ""
    return "|".join(str(value) for value in values)


def validate_industrial_vehicle_coverage(
    document: Mapping[str, object],
) -> tuple[IndustrialVehicleCoverageRow, ...]:
    policy = document.get("policy")
    metals = document.get("metals")
    if not isinstance(policy, Mapping) or not isinstance(metals, list):
        raise ValueError("industrial coverage document must contain policy and metals")
    if policy.get("fail_closed") is not True:
        raise ValueError("industrial vehicle coverage must fail closed")

    indexed: dict[str, Mapping[str, object]] = {}
    for item in metals:
        if not isinstance(item, Mapping):
            raise ValueError("metal records must be objects")
        metal_id = str(item.get("metal_id", "")).strip().lower()
        if not metal_id or metal_id in indexed:
            raise ValueError("metal identifiers must be present and unique")
        indexed[metal_id] = item

    if set(indexed) != set(REQUIRED_METALS):
        raise ValueError("industrial coverage must exactly match required metals")

    rows: list[IndustrialVehicleCoverageRow] = []
    for metal_id in REQUIRED_METALS:
        item = indexed[metal_id]
        status = str(item.get("coverage_status", "")).upper()
        if status not in ALLOWED_COVERAGE_STATUSES:
            raise ValueError(f"invalid coverage status for {metal_id}: {status}")
        ticker = item.get("approved_vehicle_ticker")
        eligible = item.get("selection_eligible") is True
        if eligible and (not ticker or status in {"RESEARCH_ONLY", "NO_APPROVED_VEHICLE"}):
            raise ValueError(f"ineligible coverage state marked selectable for {metal_id}")
        if not str(item.get("decision_reason", "")).strip():
            raise ValueError(f"decision reason required for {metal_id}")
        rows.append(
            IndustrialVehicleCoverageRow(
                metal_id=metal_id,
                benchmark_symbol=str(item.get("benchmark_symbol") or "") or None,
                coverage_status=status,
                approved_vehicle_ticker=str(ticker or "") or None,
                candidate_vehicles=_join(item.get("candidate_vehicles")),
                candidate_structure=str(item.get("candidate_structure") or "") or None,
                candidate_exposure=str(item.get("candidate_exposure") or "") or None,
                decision_reason=str(item["decision_reason"]),
                selection_eligible=eligible,
                source_refs=_join(item.get("source_refs")),
                validation_status="PASS",
            )
        )
    return tuple(rows)


def summarize_industrial_vehicle_coverage(
    rows: Iterable[IndustrialVehicleCoverageRow],
) -> dict[str, object]:
    materialized = tuple(rows)
    eligible = sum(row.selection_eligible for row in materialized)
    research_only = sum(row.coverage_status == "RESEARCH_ONLY" for row in materialized)
    return {
        "status": "PASS" if len(materialized) == len(REQUIRED_METALS) else "FAIL",
        "metal_count": len(materialized),
        "eligible_metal_count": eligible,
        "research_only_count": research_only,
        "blocked_metal_count": len(materialized) - eligible,
        "fail_closed": True,
    }


def publish_industrial_vehicle_coverage(
    rows: Iterable[IndustrialVehicleCoverageRow],
    summary: Mapping[str, object],
    output_root: Path,
) -> None:
    materialized = tuple(rows)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "industrial_vehicle_coverage.json").write_text(
        json.dumps([asdict(row) for row in materialized], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_root / "industrial_vehicle_coverage_summary.json").write_text(
        json.dumps(dict(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with (output_root / "industrial_vehicle_coverage.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        fieldnames = list(asdict(materialized[0]).keys()) if materialized else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            for row in materialized:
                writer.writerow(asdict(row))
