from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_CYCLE_ID = "metals-20260814T232103Z-6f1943b6"
EXPECTED_PACKAGE_ID = "metals-20260814T232106Z-f3577228"
EXPECTED_IMPORT_ID = "76b3106a-de26-42d9-a802-434612a2fb02"
EXPECTED_DATA_AS_OF = "2026-08-14T23:21:06.588145+00:00"
EXPECTED_ROWS_IMPORTED = 62
EXPECTED_VEHICLES = 11
EXPECTED_REGISTRY_ASSETS = 10
EXPECTED_PROVIDER_COUNTS = {"eia": 1, "world_bank": 8}


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Required evidence missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Record fail-closed R2 Metals fresh rehearsal evidence.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "project_control" / "generated" / "r2_refreshed_data_rehearsal" / "metals_r2_rehearsal_evidence.json",
    )
    args = parser.parse_args()

    operations_root = ROOT / "data" / "operations" / "metals"
    cycle = load_json(operations_root / "cycle_history" / "latest.json")
    success = load_json(operations_root / "cycle_history" / "latest_success.json")
    readiness = load_json(operations_root / "latest_readiness.json")
    operations_status = load_json(operations_root / "metals_operations_status.json")
    overlay_summary = load_json(operations_root / "daily_market_overlay" / "overlay_summary.json")

    if cycle.get("status") != "PASS":
        raise RuntimeError(f"Latest Metals cycle is not PASS: {cycle.get('status')}")
    if success.get("cycle_id") != cycle.get("cycle_id"):
        raise RuntimeError("latest_success does not match latest passing Metals cycle.")
    if cycle.get("cycle_id") != EXPECTED_CYCLE_ID:
        raise RuntimeError(f"Unexpected Metals cycle ID: {cycle.get('cycle_id')}")
    if cycle.get("package_id") != EXPECTED_PACKAGE_ID:
        raise RuntimeError(f"Unexpected Metals package ID: {cycle.get('package_id')}")
    if cycle.get("import_id") != EXPECTED_IMPORT_ID:
        raise RuntimeError(f"Unexpected Metals import ID: {cycle.get('import_id')}")
    if cycle.get("data_as_of_date") != EXPECTED_DATA_AS_OF:
        raise RuntimeError(f"Unexpected Metals data-as-of: {cycle.get('data_as_of_date')}")
    if cycle.get("failed_stage") is not None:
        raise RuntimeError(f"Metals cycle reports failed stage: {cycle.get('failed_stage')}")
    if cycle.get("errors"):
        raise RuntimeError(f"Metals cycle reports errors: {cycle.get('errors')}")
    if cycle.get("warnings"):
        raise RuntimeError(f"Metals cycle reports warnings: {cycle.get('warnings')}")

    stage_status = {str(row.get("name")): row for row in cycle.get("stages", [])}
    for stage in ("universal_export", "transactional_import", "production_readiness"):
        row = stage_status.get(stage)
        if not row or row.get("status") != "PASS" or int(row.get("return_code", 1)) != 0:
            raise RuntimeError(f"Required Metals stage did not pass: {stage}")

    import_output = str(stage_status["transactional_import"].get("stdout_tail") or "")
    if f"Rows imported: {EXPECTED_ROWS_IMPORTED}" not in import_output:
        raise RuntimeError("Transactional import did not report 62 imported rows.")

    if readiness.get("status") != "PASS" or readiness.get("ready") is not True:
        raise RuntimeError(f"Metals readiness did not pass: {readiness}")
    if readiness.get("failed_components"):
        raise RuntimeError(f"Metals readiness contains failed components: {readiness.get('failed_components')}")

    components = {str(row.get("name")): row for row in readiness.get("components", [])}
    expected_components = {
        "registry",
        "bridge_handoff",
        "package",
        "model_parity",
        "vehicle_constraints",
        "official_providers",
    }
    if set(components) != expected_components:
        raise RuntimeError(f"Unexpected readiness components: {sorted(components)}")
    if any(row.get("status") != "PASS" for row in components.values()):
        raise RuntimeError("One or more Metals readiness components are not PASS.")

    registry_detail = components["registry"].get("detail") or {}
    if int(registry_detail.get("assets", 0)) != EXPECTED_REGISTRY_ASSETS:
        raise RuntimeError("Metals registry asset count changed.")
    if int(registry_detail.get("vehicles", 0)) != EXPECTED_VEHICLES:
        raise RuntimeError("Metals registry vehicle count changed.")

    provider_detail = components["official_providers"].get("detail") or {}
    provider_counts = provider_detail.get("counts") or {}
    normalized_counts = {str(k): int(v) for k, v in provider_counts.items()}
    if normalized_counts != EXPECTED_PROVIDER_COUNTS:
        raise RuntimeError(f"Unexpected official-provider counts: {normalized_counts}")

    if overlay_summary.get("status") != "PASS":
        raise RuntimeError(f"Metals daily overlay did not pass: {overlay_summary}")
    if int(overlay_summary.get("vehicle_count", 0)) != EXPECTED_VEHICLES:
        raise RuntimeError("Metals daily overlay vehicle count changed.")
    if int(overlay_summary.get("current_vehicle_count", 0)) != EXPECTED_VEHICLES:
        raise RuntimeError("Not all Metals vehicles are current.")
    if int(overlay_summary.get("alert_count", 0)) != 0:
        raise RuntimeError("Metals daily overlay produced alerts.")
    if int(overlay_summary.get("critical_alert_count", 0)) != 0:
        raise RuntimeError("Metals daily overlay produced critical alerts.")
    if str(overlay_summary.get("highest_alert_severity")) != "INFO":
        raise RuntimeError("Unexpected Metals highest alert severity.")

    evidence = {
        "status": "UIP_R2_METALS_FRESH_REHEARSAL_PASS",
        "source_domain": "metals",
        "source_boundary": "UIP_NATIVE_METALS_RUNTIME",
        "cycle_id": cycle["cycle_id"],
        "package_id": cycle["package_id"],
        "import_id": cycle["import_id"],
        "data_as_of": cycle["data_as_of_date"],
        "cycle_started_at_utc": cycle.get("started_at_utc"),
        "cycle_completed_at_utc": cycle.get("completed_at_utc"),
        "cycle_runtime_seconds": cycle.get("runtime_seconds"),
        "rows_imported": EXPECTED_ROWS_IMPORTED,
        "required_stages": {
            name: {
                "status": stage_status[name].get("status"),
                "return_code": stage_status[name].get("return_code"),
                "runtime_seconds": stage_status[name].get("runtime_seconds"),
            }
            for name in ("universal_export", "transactional_import", "production_readiness")
        },
        "production_readiness": {
            "status": readiness.get("status"),
            "ready": readiness.get("ready"),
            "component_count": readiness.get("component_count"),
            "failed_components": readiness.get("failed_components"),
            "registry_assets": EXPECTED_REGISTRY_ASSETS,
            "registry_vehicles": EXPECTED_VEHICLES,
            "official_provider_counts": EXPECTED_PROVIDER_COUNTS,
            "official_provider_records": int(provider_detail.get("records", 0)),
            "model_parity_checks": int((components["model_parity"].get("detail") or {}).get("checks", 0)),
            "vehicle_constraint_scenarios": int((components["vehicle_constraints"].get("detail") or {}).get("scenarios", 0)),
        },
        "daily_market_overlay": {
            "status": overlay_summary.get("status"),
            "vehicle_count": EXPECTED_VEHICLES,
            "current_vehicle_count": EXPECTED_VEHICLES,
            "alert_count": 0,
            "critical_alert_count": 0,
            "highest_alert_severity": "INFO",
            "generated_at_utc": overlay_summary.get("generated_at_utc"),
        },
        "operations_status_present": bool(operations_status),
        "live_official_providers_executed": True,
        "daily_market_collection_executed": True,
        "native_semantics_reinterpreted": False,
        "cross_asset_rank_created": False,
        "automatic_purchase_execution_created": False,
        "next_gate": "R2_CRYPTO_RECOVERY_AND_FRESH_REHEARSAL",
    }

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(evidence, indent=2, sort_keys=True))
    print("UIP_R2_METALS_FRESH_REHEARSAL=PASS")
    print(f"EVIDENCE_OUTPUT={output}")
    print("NEXT_GATE=R2_CRYPTO_RECOVERY_AND_FRESH_REHEARSAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
