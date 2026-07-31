from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(
    r"C:\Users\DevonLockard\InvestmentPlatform-MTG-Reconciliation"
)

INVENTORY_ROOT = (
    REPO
    / "docs"
    / "project_control"
    / "generated"
    / "mtg_orchestration_inventory"
)

RAW_INVENTORY = (
    INVENTORY_ROOT
    / "mtg_orchestration_file_inventory.csv"
)

CANONICAL_ROOT = Path(
    r"C:\Users\DevonLockard\mtg-investment-terminal"
)

SECONDARY_ROOT = Path(
    r"C:\Users\DevonLockard\mtg-source"
)

EXCLUDED_TOP_LEVELS = {
    "artifacts",
    "data",
    "docs",
    "tests",
}

EXCLUDED_PATH_PARTS = {
    "__pycache__",
    "archive",
    "archives",
    "backup",
    "backups",
    "code_backups",
    "hotfix_backups",
    "hosted_source_backups",
    "repair_input",
    "recovery",
    "payload",
    "pilot_execution",
    "weekend_readiness",
}

EXCLUDED_FILENAME_MARKERS = {
    "_backup",
    "_before_",
    "_old",
    "_copy",
    "test_",
}

ORCHESTRATION_FILENAME_MARKERS = (
    "run_",
    "daily",
    "production",
    "delivery",
    "handoff",
    "export",
    "refresh",
    "pipeline",
    "orchestrat",
    "lifecycle",
    "run_all",
)

PRIORITY_PATHS = {
    "run.py",
    "terminal2_daily_update.py",
    "terminal2_lifecycle.py",
    "terminal2_run_all.py",
    "scripts/build_mtg_hosted_uip_delivery.py",
    "scripts/build_mtg_uip_export.py",
    "scripts/build_phase_10_10_universal_export.py",
    "scripts/run_certified_marketplace_decisioning.py",
    "scripts/run_daily_ebay_collection.py",
    "scripts/run_daily_tcgcsv_collection.py",
    "scripts/run_mtg_marketplace_production.py",
    "scripts/run_phase_11e_12_accumulation_cycle.py",
    "scripts/run_phase_11e_13_valuation_integration.py",
    "scripts/run_phase_11e_14_consumption_integration.py",
    "scripts/run_phase_11e_15_production_delivery.py",
    "scripts/run_phase_11e_17_manual_uip_handoff.py",
    "scripts/run_secret_lair_production_refresh.py",
    "scripts/run_universal_mtg_history_production.py",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def write_rows(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def exclusion_reason(relative_path: str) -> str | None:
    path = Path(relative_path)
    parts_lower = [
        part.lower()
        for part in path.parts
    ]

    if not parts_lower:
        return "empty_path"

    if parts_lower[0] in EXCLUDED_TOP_LEVELS:
        return f"excluded_top_level:{parts_lower[0]}"

    for part in parts_lower:
        if part in EXCLUDED_PATH_PARTS:
            return f"excluded_path_part:{part}"

        if any(
            marker in part
            for marker in (
                "_code_backups",
                "_hotfix_backups",
                "_repair_input",
                "_recovery",
            )
        ):
            return f"excluded_generated_copy:{part}"

    name_lower = path.name.lower()

    if name_lower.startswith("test_"):
        return "test_file"

    if path.suffix.lower() == ".json":
        return "generated_json"

    if any(
        marker in name_lower
        for marker in EXCLUDED_FILENAME_MARKERS
    ):
        return "backup_or_test_filename"

    return None


def is_orchestration_candidate(
    row: dict[str, str],
) -> bool:
    relative_path = row["relative_path"]
    name_lower = Path(relative_path).name.lower()

    if relative_path in PRIORITY_PATHS:
        return True

    if row["has_main_guard"].lower() != "true":
        return False

    return any(
        marker in name_lower
        for marker in ORCHESTRATION_FILENAME_MARKERS
    )


def classify_candidate(relative_path: str) -> str:
    name = Path(relative_path).name.lower()

    if "daily" in name or "refresh" in name:
        return "scheduled_collection_or_refresh"

    if "production" in name:
        return "production_pipeline"

    if "handoff" in name or "delivery" in name:
        return "uip_delivery_or_handoff"

    if "export" in name:
        return "export_publication"

    if "marketplace" in name:
        return "marketplace_orchestration"

    if "history" in name:
        return "historical_orchestration"

    if "lifecycle" in name or "run_all" in name:
        return "aggregate_orchestration"

    return "other_entrypoint"


def main() -> int:
    rows = read_rows(RAW_INVENTORY)

    canonical_rows = [
        row
        for row in rows
        if Path(row["source_root"]) == CANONICAL_ROOT
    ]

    secondary_rows = [
        row
        for row in rows
        if Path(row["source_root"]) == SECONDARY_ROOT
    ]

    secondary_by_path = {
        row["relative_path"]: row
        for row in secondary_rows
    }

    retained: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for row in canonical_rows:
        reason = exclusion_reason(
            row["relative_path"]
        )

        if reason is not None:
            excluded.append(
                {
                    **row,
                    "exclusion_reason": reason,
                }
            )
            continue

        if not is_orchestration_candidate(row):
            continue

        secondary = secondary_by_path.get(
            row["relative_path"]
        )

        duplicate_status = "canonical_only"

        if secondary is not None:
            duplicate_status = (
                "identical_in_secondary"
                if secondary["sha256"] == row["sha256"]
                else "different_in_secondary"
            )

        retained.append(
            {
                **row,
                "orchestration_category": (
                    classify_candidate(
                        row["relative_path"]
                    )
                ),
                "secondary_copy_status": (
                    duplicate_status
                ),
                "priority_candidate": (
                    row["relative_path"]
                    in PRIORITY_PATHS
                ),
            }
        )

    retained.sort(
        key=lambda row: (
            not row["priority_candidate"],
            row["orchestration_category"],
            row["relative_path"].lower(),
        )
    )

    candidate_fields = [
        "source_root",
        "relative_path",
        "suffix",
        "size_bytes",
        "sha256",
        "likely_entrypoint",
        "has_main_guard",
        "python_functions",
        "python_classes",
        "imports",
        "detected_side_effects",
        "orchestration_category",
        "secondary_copy_status",
        "priority_candidate",
    ]

    write_rows(
        INVENTORY_ROOT
        / "mtg_canonical_orchestration_candidates.csv",
        retained,
        candidate_fields,
    )

    duplicate_rows = [
        {
            "relative_path": row["relative_path"],
            "secondary_copy_status": (
                row["secondary_copy_status"]
            ),
            "canonical_sha256": row["sha256"],
            "secondary_sha256": (
                secondary_by_path.get(
                    row["relative_path"],
                    {},
                ).get("sha256", "")
            ),
        }
        for row in retained
    ]

    write_rows(
        INVENTORY_ROOT
        / "mtg_source_overlap.csv",
        duplicate_rows,
        [
            "relative_path",
            "secondary_copy_status",
            "canonical_sha256",
            "secondary_sha256",
        ],
    )

    category_counts = Counter(
        row["orchestration_category"]
        for row in retained
    )

    overlap_counts = Counter(
        row["secondary_copy_status"]
        for row in retained
    )

    summary = {
        "generated_at_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "execution_mode": (
            "READ_ONLY_RAW_INVENTORY_REDUCTION"
        ),
        "canonical_source_root": str(
            CANONICAL_ROOT
        ),
        "secondary_source_root": str(
            SECONDARY_ROOT
        ),
        "raw_canonical_rows": len(
            canonical_rows
        ),
        "raw_secondary_rows": len(
            secondary_rows
        ),
        "retained_orchestration_candidates": len(
            retained
        ),
        "priority_candidates": sum(
            bool(row["priority_candidate"])
            for row in retained
        ),
        "excluded_rows": len(excluded),
        "category_counts": dict(
            sorted(category_counts.items())
        ),
        "secondary_overlap_counts": dict(
            sorted(overlap_counts.items())
        ),
    }

    (
        INVENTORY_ROOT
        / "mtg_canonical_orchestration_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "MTG CANONICAL ORCHESTRATION REDUCTION: COMPLETE"
    )
    print(
        "Canonical raw rows:",
        len(canonical_rows),
    )
    print(
        "Retained candidates:",
        len(retained),
    )
    print(
        "Priority candidates:",
        summary["priority_candidates"],
    )
    print(
        "Secondary overlap:",
        dict(overlap_counts),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
