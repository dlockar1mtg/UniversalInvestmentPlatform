from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb


REQUIRED_SUPPORT = {
    "latest_forecast_model_components.csv": {
        "forecast_run_id", "metal", "horizon_months", "model_name", "model_forecast", "model_weight"
    },
    "latest_learned_regime_probabilities.csv": {
        "forecast_run_id", "metal", "regime", "probability"
    },
    "latest_uncertainty_adjusted_views.csv": {
        "forecast_run_id", "ticker", "metal", "horizon_months", "raw_expected_return",
        "uncertainty_penalty", "downside_penalty", "adjusted_expected_return"
    },
    "latest_recommendation_change_explanations.csv": set(),
    "latest_data_freshness_details.csv": set(),
    "latest_platform_health_score.csv": set(),
}

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv_summary(path: Path, required_columns: set[str]) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        missing = sorted(required_columns - set(columns))
        rows = list(reader)
    populated: dict[str, int] = {}
    for column in columns:
        populated[column] = sum(
            1 for row in rows if row.get(column) not in (None, "", "NA", "NaN", "nan", "null", "None")
        )
    return {
        "file": str(path),
        "rows": len(rows),
        "columns": columns,
        "missing_required_columns": missing,
        "populated_counts": populated,
    }


def current_metals_package_id(database: Path) -> str:
    connection = duckdb.connect(str(database), read_only=True)
    try:
        row = connection.execute(
            """
            SELECT last_package_id
            FROM universal_domain_operational_status
            WHERE lower(domain_id)='metals'
            """
        ).fetchone()
        if row and row[0]:
            return str(row[0])
        row = connection.execute(
            """
            SELECT _package_id
            FROM universal_row_lineage
            WHERE lower(platform_id)='metals' AND _package_id IS NOT NULL
            ORDER BY _imported_at_utc DESC
            LIMIT 1
            """
        ).fetchone()
        if not row or not row[0]:
            raise RuntimeError("Current Metals package ID is not available in UIP authority.")
        return str(row[0])
    finally:
        connection.close()


def candidate_packages(search_root: Path, package_id: str) -> list[Path]:
    if not search_root.exists():
        return []
    candidates: set[Path] = set()
    for path in search_root.rglob("package_summary.json"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(payload.get("package_id", "")) == package_id:
            candidates.add(path.parent.resolve())
    for path in search_root.rglob(package_id):
        if path.is_dir() and not any(part in SKIP_DIRS for part in path.parts):
            candidates.add(path.resolve())
    return sorted(candidates, key=lambda item: str(item).lower())


def audit_package(package_root: Path) -> dict[str, Any]:
    support_root = package_root / "supporting_native"
    result: dict[str, Any] = {
        "package_root": str(package_root),
        "supporting_native_root": str(support_root),
        "complete": True,
        "files": {},
    }
    for filename, required_columns in REQUIRED_SUPPORT.items():
        path = support_root / filename
        if not path.is_file():
            result["complete"] = False
            result["files"][filename] = {"present": False}
            continue
        summary = read_csv_summary(path, required_columns)
        summary["present"] = True
        if summary["missing_required_columns"]:
            result["complete"] = False
        result["files"][filename] = summary
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of promotable Metals-native evidence retained in the certified package.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--search-root", type=Path, action="append", required=True)
    args = parser.parse_args()

    before = sha256_file(args.database)
    expected = args.expected_sha256.lower()
    if before.lower() != expected:
        raise RuntimeError(f"Database SHA-256 mismatch: {before}")

    package_id = current_metals_package_id(args.database)
    discovered: list[Path] = []
    for root in args.search_root:
        discovered.extend(candidate_packages(root, package_id))
    unique = sorted({item.resolve() for item in discovered}, key=lambda item: str(item).lower())
    audits = [audit_package(path) for path in unique]

    after = sha256_file(args.database)
    if after.lower() != expected:
        raise RuntimeError("Database changed during read-only Metals native-evidence audit.")

    complete = [item for item in audits if item["complete"]]
    payload = {
        "status": "PASS" if complete else "BLOCKED",
        "read_only": True,
        "database_sha256": after,
        "current_metals_package_id": package_id,
        "search_roots": [str(path) for path in args.search_root],
        "candidate_packages": audits,
        "complete_package_count": len(complete),
        "next_decision": (
            "PROMOTE_EXISTING_NATIVE_EVIDENCE" if complete else "LOCATE_OR_REBUILD_VERSIONED_EXPORT_FROM_EXISTING_NATIVE_OUTPUTS_WITHOUT_MODEL_RERUN"
        ),
    }
    print(json.dumps(payload, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
