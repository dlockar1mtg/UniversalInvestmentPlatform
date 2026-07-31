from __future__ import annotations

import csv
import json
from pathlib import Path


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

ANALYSIS_PATH = (
    INVENTORY_ROOT
    / "mtg_priority_orchestration_static_analysis.json"
)

CANDIDATE_PATH = (
    INVENTORY_ROOT
    / "mtg_canonical_orchestration_candidates.csv"
)

OUTPUT_PATH = (
    INVENTORY_ROOT
    / "mtg_orchestration_compatibility_matrix.csv"
)


def proposed_disposition(
    relative_path: str,
) -> tuple[str, str]:
    direct_replace = {
        "run.py",
        "terminal2_run_all.py",
        "terminal2_lifecycle.py",
        "terminal2_daily_update.py",
    }

    retain_standalone = {
        "scripts/run_daily_ebay_collection.py",
        "scripts/run_daily_tcgcsv_collection.py",
        "scripts/run_secret_lair_production_refresh.py",
        "scripts/run_mtg_marketplace_production.py",
        "scripts/run_universal_mtg_history_production.py",
    }

    adapt = {
        "scripts/build_mtg_hosted_uip_delivery.py",
        "scripts/build_mtg_uip_export.py",
        "scripts/build_phase_10_10_universal_export.py",
        "scripts/run_phase_11e_12_accumulation_cycle.py",
        "scripts/run_phase_11e_13_valuation_integration.py",
        "scripts/run_phase_11e_14_consumption_integration.py",
        "scripts/run_phase_11e_15_production_delivery.py",
        "scripts/run_phase_11e_17_manual_uip_handoff.py",
        "scripts/run_certified_marketplace_decisioning.py",
    }

    if relative_path in direct_replace:
        return (
            "REPLACE",
            "UIP already owns platform-level orchestration; do not port a second aggregate runner.",
        )

    if relative_path in retain_standalone:
        return (
            "RETAIN_STANDALONE",
            "Domain production collection remains outside UIP; expose certified outputs through contracts.",
        )

    if relative_path in adapt:
        return (
            "ADAPT",
            "Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment.",
        )

    return (
        "REVIEW",
        "Requires manual architectural review.",
    )


def main() -> int:
    analysis = json.loads(
        ANALYSIS_PATH.read_text(
            encoding="utf-8"
        )
    )

    analysis_by_path = {
        row["relative_path"]: row
        for row in analysis["canonical_results"]
    }

    with CANDIDATE_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        candidates = [
            row
            for row in csv.DictReader(handle)
            if row["priority_candidate"].lower()
            == "true"
        ]

    fieldnames = [
        "relative_path",
        "orchestration_category",
        "secondary_copy_status",
        "detected_side_effects",
        "line_count",
        "operational_call_count",
        "subprocess_call_count",
        "proposed_disposition",
        "rationale",
        "final_disposition",
        "review_notes",
    ]

    rows = []

    for candidate in candidates:
        relative_path = candidate[
            "relative_path"
        ]

        analysis_row = analysis_by_path.get(
            relative_path,
            {},
        )

        disposition, rationale = (
            proposed_disposition(relative_path)
        )

        rows.append(
            {
                "relative_path": relative_path,
                "orchestration_category": candidate[
                    "orchestration_category"
                ],
                "secondary_copy_status": candidate[
                    "secondary_copy_status"
                ],
                "detected_side_effects": candidate[
                    "detected_side_effects"
                ],
                "line_count": analysis_row.get(
                    "line_count",
                    "",
                ),
                "operational_call_count": len(
                    analysis_row.get(
                        "operational_calls",
                        [],
                    )
                ),
                "subprocess_call_count": len(
                    analysis_row.get(
                        "subprocess_commands",
                        [],
                    )
                ),
                "proposed_disposition": disposition,
                "rationale": rationale,
                "final_disposition": "",
                "review_notes": "",
            }
        )

    with OUTPUT_PATH.open(
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

    print("MTG COMPATIBILITY MATRIX: CREATED")
    print("Rows:", len(rows))
    print("Output:", OUTPUT_PATH)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
