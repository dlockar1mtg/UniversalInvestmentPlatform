"""Project Metals cycle evidence into dashboard-ready JSON and CSV status outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_metals_operations_status(
    *,
    latest_cycle_path: Path,
    latest_readiness_path: Path,
) -> dict[str, object]:
    cycle = _read_json(latest_cycle_path)
    readiness = _read_json(latest_readiness_path)
    components = readiness.get("components") or []
    component_status = {
        str(item.get("name")): str(item.get("status"))
        for item in components
        if isinstance(item, dict)
    }
    failed_components = readiness.get("failed_components") or []
    return {
        "cycle_id": cycle.get("cycle_id"),
        "cycle_status": cycle.get("status", "UNKNOWN"),
        "cycle_started_at_utc": cycle.get("started_at_utc"),
        "cycle_completed_at_utc": cycle.get("completed_at_utc"),
        "cycle_runtime_seconds": cycle.get("runtime_seconds"),
        "package_id": cycle.get("package_id"),
        "import_id": cycle.get("import_id"),
        "data_as_of_date": cycle.get("data_as_of_date"),
        "failed_stage": cycle.get("failed_stage"),
        "owner": cycle.get("owner"),
        "notification_destination": cycle.get("notification_destination"),
        "warning_count": len(cycle.get("warnings") or []),
        "error_count": len(cycle.get("errors") or []),
        "readiness_status": readiness.get("status", "UNKNOWN"),
        "readiness_generated_at_utc": readiness.get("generated_at_utc"),
        "readiness_component_count": readiness.get("component_count", 0),
        "readiness_failed_component_count": len(failed_components),
        "readiness_failed_components": ",".join(map(str, failed_components)),
        "provider_status": component_status.get("official_providers", "UNKNOWN"),
        "package_status": component_status.get("package", "UNKNOWN"),
        "model_parity_status": component_status.get("model_parity", "UNKNOWN"),
        "vehicle_constraints_status": component_status.get("vehicle_constraints", "UNKNOWN"),
        "registry_status": component_status.get("registry", "UNKNOWN"),
        "bridge_handoff_status": component_status.get("bridge_handoff", "UNKNOWN"),
    }


def write_metals_operations_status(status: dict[str, object], output_root: Path) -> tuple[Path, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "metals_operations_status.json"
    csv_path = output_root / "metals_operations_status.csv"
    json_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(status))
        writer.writeheader()
        writer.writerow(status)
    return json_path, csv_path
