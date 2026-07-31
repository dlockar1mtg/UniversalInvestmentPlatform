"""Profile certified MTG delivery files for the Phase 3.2 decision adapter."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(r"C:\Users\DevonLockard\InvestmentPlatform-MTG-Reconciliation")
PACKAGE = Path(
    r"C:\Users\DevonLockard\mtg-investment-terminal"
    r"\data\operations\mtg_uip_delivery\latest"
)
OUTPUT = REPO / "docs" / "project_control" / "generated" / "mtg_decision_adapter_profile"
FILES = (
    "asset_master.csv",
    "forecasts.csv",
    "recommendations.csv",
    "risk_metrics.csv",
    "historical_performance.csv",
    "portfolio_positions.csv",
    "platform_status.csv",
)
ID_CANDIDATES = (
    "universal_asset_id",
    "universal_mtg_product_id",
    "investment_product_id",
    "platform_asset_id",
    "product_id",
    "asset_id",
    "source_record_id",
)
GROUPS = {
    "name": ("asset_name", "canonical_product_name", "product_name", "name"),
    "category": ("asset_subclass", "asset_class", "product_lane", "lane", "category", "product_type"),
    "eligibility": ("forecast_eligible", "recommendation_eligible", "historical_performance_eligible", "performance_eligible", "investable", "active"),
    "tier": ("tier", "recommendation_tier", "investment_tier", "native_tier", "decision_tier", "ranking_tier"),
    "recommendation": ("recommendation", "recommendation_label", "investment_recommendation", "action", "decision"),
    "score": ("normalized_score", "score", "recommendation_score", "investment_score", "confidence_score", "risk_score"),
    "forecast": ("one_year_base_usd", "three_year_base_usd", "five_year_base_usd", "point_forecast", "expected_return", "forecast_horizon_months", "forecast_method"),
    "risk": ("risk_score", "risk_level", "volatility", "maximum_drawdown", "liquidity_score", "risk_tier"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"CSV has no header: {path}")
        columns = [str(value).strip() for value in reader.fieldnames]
        rows = [
            {
                str(key).strip(): "" if value is None else str(value).strip()
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]
    return columns, rows


def present(columns: list[str], candidates: tuple[str, ...]) -> list[str]:
    lookup = {column.lower(): column for column in columns}
    return [lookup[c.lower()] for c in candidates if c.lower() in lookup]


def first(columns: list[str], candidates: tuple[str, ...]) -> str:
    found = present(columns, candidates)
    return found[0] if found else ""


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def ids(rows: list[dict[str, str]], column: str) -> set[str]:
    if not column:
        return set()
    return {
        str(row.get(column, "")).strip().upper()
        for row in rows
        if str(row.get(column, "")).strip()
    }


def main() -> int:
    manifest = json.loads((PACKAGE / "export_manifest.json").read_text(encoding="utf-8-sig"))
    OUTPUT.mkdir(parents=True, exist_ok=True)

    profiles: dict[str, dict[str, Any]] = {}
    all_rows: dict[str, list[dict[str, str]]] = {}
    summary_rows: list[dict[str, Any]] = []
    column_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    breakdown_rows: list[dict[str, Any]] = []

    for filename in FILES:
        path = PACKAGE / filename
        columns, rows = read_csv(path)
        all_rows[filename] = rows
        identifier = first(columns, ID_CANDIDATES)
        values = [str(row.get(identifier, "")).strip() for row in rows] if identifier else []
        nonblank = [value for value in values if value]
        duplicates = sum(count - 1 for count in Counter(nonblank).values() if count > 1)
        declared = str(manifest.get("files", {}).get(filename, {}).get("sha256", "")).lower()
        actual = sha256(path)

        profile = {
            "filename": filename,
            "row_count": len(rows),
            "column_count": len(columns),
            "columns": columns,
            "selected_identifier": identifier,
            "identifier_nonblank_count": len(nonblank),
            "identifier_blank_count": len(rows) - len(nonblank),
            "identifier_unique_count": len(set(nonblank)),
            "identifier_duplicate_row_count": duplicates,
            "manifest_sha256": declared,
            "actual_sha256": actual,
            "checksum_status": "PASS" if declared == actual else "FAILED",
        }
        profiles[filename] = profile
        summary_rows.append({key: profile[key] for key in (
            "filename", "row_count", "column_count", "selected_identifier",
            "identifier_nonblank_count", "identifier_blank_count",
            "identifier_unique_count", "identifier_duplicate_row_count", "checksum_status"
        )})

        for column in columns:
            vals = [str(row.get(column, "")).strip() for row in rows]
            nonblank_vals = [value for value in vals if value]
            samples = list(dict.fromkeys(nonblank_vals))[:8]
            column_rows.append({
                "filename": filename,
                "column_name": column,
                "nonblank_count": len(nonblank_vals),
                "blank_count": len(vals) - len(nonblank_vals),
                "distinct_nonblank_count": len(set(nonblank_vals)),
                "sample_values": json.dumps(samples),
            })

        for group, candidates in {"identifier": ID_CANDIDATES, **GROUPS}.items():
            found = present(columns, candidates)
            candidate_rows.append({
                "filename": filename,
                "field_group": group,
                "present_columns": "|".join(found),
                "present_count": len(found),
            })
            for column in found:
                counts = Counter(str(row.get(column, "")).strip() or "<BLANK>" for row in rows)
                for value, count in counts.most_common():
                    breakdown_rows.append({
                        "filename": filename,
                        "field_group": group,
                        "column": column,
                        "value": value,
                        "row_count": count,
                    })

    asset_ids = ids(all_rows["asset_master.csv"], profiles["asset_master.csv"]["selected_identifier"])
    join_rows: list[dict[str, Any]] = []
    for filename in FILES:
        if filename in {"platform_status.csv", "portfolio_positions.csv"}:
            continue
        dataset_ids = ids(all_rows[filename], profiles[filename]["selected_identifier"])
        matched = dataset_ids & asset_ids
        join_rows.append({
            "filename": filename,
            "identifier_column": profiles[filename]["selected_identifier"],
            "unique_ids": len(dataset_ids),
            "ids_matching_asset_master": len(matched),
            "ids_missing_from_asset_master": len(dataset_ids - asset_ids),
            "asset_master_ids_missing_from_dataset": len(asset_ids - dataset_ids),
            "coverage_pct_of_asset_master": round(len(matched) / len(asset_ids) * 100, 4) if asset_ids else 0,
        })

    write_csv(OUTPUT / "dataset_summary.csv", summary_rows, list(summary_rows[0]))
    write_csv(OUTPUT / "column_profiles.csv", column_rows, list(column_rows[0]))
    write_csv(OUTPUT / "key_field_candidates.csv", candidate_rows, list(candidate_rows[0]))
    write_csv(OUTPUT / "decision_field_breakdowns.csv", breakdown_rows, list(breakdown_rows[0]))
    write_csv(OUTPUT / "join_coverage.csv", join_rows, list(join_rows[0]))

    summary = {
        "profile_status": "PASS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "package_id": manifest.get("package_id"),
        "certified_product_count": manifest.get("products"),
        "asset_master_rows": profiles["asset_master.csv"]["row_count"],
        "asset_master_unique_products": profiles["asset_master.csv"]["identifier_unique_count"],
        "forecast_rows": profiles["forecasts.csv"]["row_count"],
        "recommendation_rows": profiles["recommendations.csv"]["row_count"],
        "risk_metric_rows": profiles["risk_metrics.csv"]["row_count"],
        "historical_performance_rows": profiles["historical_performance.csv"]["row_count"],
        "all_checksums_pass": all(p["checksum_status"] == "PASS" for p in profiles.values()),
        "all_1141_products_reconciled": profiles["asset_master.csv"]["identifier_unique_count"] == 1141,
    }
    (OUTPUT / "profile_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT / "dataset_profiles.json").write_text(json.dumps(profiles, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("=" * 78)
    print("MTG DECISION ADAPTER SOURCE PROFILE")
    print("=" * 78)
    for row in summary_rows:
        print(
            f"{row['filename']}: rows={row['row_count']}, "
            f"id={row['selected_identifier'] or '<none>'}, "
            f"unique={row['identifier_unique_count']}, "
            f"blank={row['identifier_blank_count']}, "
            f"duplicates={row['identifier_duplicate_row_count']}, "
            f"checksum={row['checksum_status']}"
        )
    print("\nJoin coverage against asset_master:")
    for row in join_rows:
        print(
            f"{row['filename']}: matched={row['ids_matching_asset_master']}, "
            f"missing_from_master={row['ids_missing_from_asset_master']}, "
            f"master_without_dataset={row['asset_master_ids_missing_from_dataset']}, "
            f"coverage={row['coverage_pct_of_asset_master']}%"
        )
    print("\n" + json.dumps(summary, indent=2, sort_keys=True))
    print("\nOutput:", OUTPUT)

    if not summary["all_checksums_pass"]:
        raise RuntimeError("One or more package checksums failed.")
    if not summary["all_1141_products_reconciled"]:
        raise RuntimeError("Asset master does not reconcile to 1,141 unique products.")

    print("\nMTG DECISION ADAPTER SOURCE PROFILE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
