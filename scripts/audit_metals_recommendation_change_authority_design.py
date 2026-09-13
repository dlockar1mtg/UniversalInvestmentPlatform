"""Read-only design audit for a future UIP-native Metals recommendation-change authority.

This audit does not create recommendation-change rows. It inventories the restored
presentation family, inspects the latest UIP-native recommendation output, and checks
whether the current runtime persists enough native recommendation history to compute
real changes across runs without copying legacy rows or projecting commodity state to
vehicles.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_DECISION_BLOCKED = "DO_NOT_AUTHORIZE_RECOMMENDATION_CHANGE_V1_NO_NATIVE_RECOMMENDATION_HISTORY"
EXPECTED_DECISION_READY = "AUTHORIZE_UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1_DESIGN"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lineage-evidence", type=Path, required=True)
    parser.add_argument("--native-cycle", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--store-source", type=Path, required=True)
    parser.add_argument("--cycle-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lineage = read_json(args.lineage_evidence)
    native_cycle = read_json(args.native_cycle)
    store_source = args.store_source.read_text(encoding="utf-8-sig")
    cycle_source = args.cycle_source.read_text(encoding="utf-8-sig")

    restored = ((lineage.get("record_types") or {}).get("metals_recommendation_change") or {})
    restored_count = int(restored.get("count", 0))
    restored_keys = sorted(str(value) for value in restored.get("payload_keys", []))
    restored_lineage = restored.get("distinct_standard_lineage", [])

    forecasts = native_cycle.get("forecasts") or []
    recommendation_rows = [row for row in forecasts if str(row.get("recommendation") or "").strip()]
    asset_ids = sorted({str(row.get("asset_id") or "").strip() for row in recommendation_rows if str(row.get("asset_id") or "").strip()})
    horizons = sorted({int(row.get("horizon_months")) for row in recommendation_rows if row.get("horizon_months") is not None})
    recommendation_values = sorted({str(row.get("recommendation") or "").strip() for row in recommendation_rows})

    artifact_files = sorted(
        path.relative_to(args.artifact_root).as_posix()
        for path in args.artifact_root.rglob("*")
        if path.is_file()
    )
    native_cycle_snapshots = [name for name in artifact_files if name.endswith("native_cycle/latest.json")]
    native_cycle_csvs = [name for name in artifact_files if name.endswith("native_cycle/latest_forecasts.csv")]

    persistent_recommendation_table_declared = (
        "CREATE TABLE IF NOT EXISTS metals_native_forecasts" in store_source
        or "CREATE TABLE IF NOT EXISTS metals_native_recommend" in store_source
        or "CREATE TABLE IF NOT EXISTS metals_recommendation" in store_source
    )
    latest_only_publication = '"latest.json"' in cycle_source and '"latest_forecasts.csv"' in cycle_source

    checks = {
        "restored_recommendation_change_family_present": restored_count > 0,
        "restored_recommendation_change_schema_observed": len(restored_keys) > 0,
        "native_cycle_pass": native_cycle.get("status") == "PASS",
        "native_recommendations_present": len(recommendation_rows) > 0,
        "native_recommendations_have_assets": len(asset_ids) > 0,
        "native_recommendations_have_horizons": len(horizons) > 0,
        "production_artifact_contains_latest_native_cycle": len(native_cycle_snapshots) == 1,
        "production_artifact_contains_latest_forecast_csv": len(native_cycle_csvs) == 1,
        "runtime_uses_latest_only_publication_names": latest_only_publication,
        "persistent_native_recommendation_history_declared": persistent_recommendation_table_declared,
    }

    history_ready = (
        persistent_recommendation_table_declared
        or len(native_cycle_snapshots) > 1
        or len(native_cycle_csvs) > 1
    )
    design_ready = (
        checks["restored_recommendation_change_family_present"]
        and checks["restored_recommendation_change_schema_observed"]
        and checks["native_cycle_pass"]
        and checks["native_recommendations_present"]
        and history_ready
    )
    decision = EXPECTED_DECISION_READY if design_ready else EXPECTED_DECISION_BLOCKED

    evidence = {
        "status": "METALS_RECOMMENDATION_CHANGE_AUTHORITY_DESIGN_AUDIT_PASS",
        "decision": decision,
        "query_policy": "ARTIFACT_AND_SOURCE_READ_ONLY",
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "legacy_equivalent": False,
        "restored_recommendation_change": {
            "row_count": restored_count,
            "payload_keys": restored_keys,
            "distinct_standard_lineage": restored_lineage,
        },
        "current_native_recommendations": {
            "cycle_status": native_cycle.get("status"),
            "forecast_count": len(forecasts),
            "recommendation_row_count": len(recommendation_rows),
            "asset_count": len(asset_ids),
            "assets": asset_ids,
            "horizons_months": horizons,
            "recommendation_values": recommendation_values,
            "authority_scope": "COMMODITY_FORECAST_ROWS",
        },
        "native_recommendation_history": {
            "persistent_history_table_declared": persistent_recommendation_table_declared,
            "latest_only_publication_names": latest_only_publication,
            "artifact_native_cycle_snapshot_count": len(native_cycle_snapshots),
            "artifact_native_cycle_csv_count": len(native_cycle_csvs),
            "history_ready_for_change_detection": history_ready,
        },
        "checks": checks,
        "missing_semantics_to_govern_before_builder": [
            "durable UIP-native recommendation history across production runs",
            "canonical comparison key (asset plus horizon or asset-level recommendation)",
            "change-event schema and effective timestamp semantics",
            "initial-observation behavior",
            "policy for methodology-version changes between compared recommendations",
            "commodity-only authority boundary; no silent commodity-to-vehicle projection",
        ],
        "notes": [
            "Current UIP-native Metals recommendations are available only in the latest native-cycle output.",
            "A genuine recommendation change requires at least two durable native recommendation states.",
            "Restored recommendation-change rows are evidence only and must not be copied forward as fresh.",
            "The historical restored family must not be treated as equivalent to a new UIP-native authority.",
            "If recommendation history is added later, design authorization still precedes any builder or production wiring.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print(f"METALS_RECOMMENDATION_CHANGE_AUTHORITY_DESIGN={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
