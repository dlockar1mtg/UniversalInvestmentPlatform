"""Metals operations visibility, history projection, and alert classification."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class MetalsAlert:
    severity: str
    code: str
    message: str
    component: str


_SEVERITY_RANK = {"INFO": 0, "WARNING": 1, "CRITICAL": 2}


def _parse_time(value: object) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _component_map(readiness: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {
        str(item.get("name")): item
        for item in readiness.get("components", [])
        if isinstance(item, Mapping)
    }


def classify_metals_alerts(
    cycle: Mapping[str, object],
    readiness: Mapping[str, object],
    *,
    as_of: datetime | None = None,
    warning_package_age_seconds: int = 604800,
    critical_package_age_seconds: int = 3888000,
) -> tuple[MetalsAlert, ...]:
    now = (as_of or datetime.now(timezone.utc)).astimezone(timezone.utc)
    alerts: list[MetalsAlert] = []
    if str(cycle.get("status", "")).upper() != "PASS":
        alerts.append(MetalsAlert("CRITICAL", "CYCLE_FAILED", "Latest Metals cycle did not pass.", "cycle"))
    if cycle.get("failed_stage"):
        alerts.append(MetalsAlert("CRITICAL", "STAGE_FAILED", f"Required stage failed: {cycle['failed_stage']}", str(cycle["failed_stage"])))
    if not cycle.get("package_id"):
        alerts.append(MetalsAlert("CRITICAL", "PACKAGE_ID_MISSING", "Latest cycle has no package identifier.", "package"))
    if not cycle.get("import_id"):
        alerts.append(MetalsAlert("CRITICAL", "IMPORT_ID_MISSING", "Latest cycle has no import identifier.", "import"))
    if str(readiness.get("status", "")).upper() != "PASS" or not readiness.get("ready"):
        alerts.append(MetalsAlert("CRITICAL", "READINESS_FAILED", "Metals readiness gate did not pass.", "readiness"))
    components = _component_map(readiness)
    for name, item in components.items():
        if str(item.get("status", "")).upper() != "PASS":
            alerts.append(MetalsAlert("CRITICAL", "COMPONENT_FAILED", f"Readiness component failed: {name}", name))
    package = components.get("package", {})
    detail = package.get("detail", {}) if isinstance(package, Mapping) else {}
    age_seconds = detail.get("age_seconds") if isinstance(detail, Mapping) else None
    if age_seconds is not None:
        age = int(age_seconds)
        if age > critical_package_age_seconds:
            alerts.append(MetalsAlert("CRITICAL", "PACKAGE_STALE", "Latest Metals package exceeds the critical freshness threshold.", "package"))
        elif age > warning_package_age_seconds:
            alerts.append(MetalsAlert("WARNING", "PACKAGE_AGING", "Latest Metals package exceeds the warning freshness threshold.", "package"))
    completed = _parse_time(cycle.get("completed_at_utc"))
    if completed and completed > now:
        alerts.append(MetalsAlert("CRITICAL", "FUTURE_CYCLE", "Latest cycle completion time is in the future.", "cycle"))
    if cycle.get("errors"):
        alerts.append(MetalsAlert("CRITICAL", "CYCLE_ERRORS", f"Latest cycle recorded {len(cycle['errors'])} error(s).", "cycle"))
    if cycle.get("warnings"):
        alerts.append(MetalsAlert("WARNING", "CYCLE_WARNINGS", f"Latest cycle recorded {len(cycle['warnings'])} warning(s).", "cycle"))
    return tuple(sorted(alerts, key=lambda item: (-_SEVERITY_RANK[item.severity], item.code)))


def build_metals_operations_snapshot(cycle: Mapping[str, object], readiness: Mapping[str, object], *, as_of: datetime | None = None) -> dict[str, object]:
    components = _component_map(readiness)
    package_detail = components.get("package", {}).get("detail", {}) if components.get("package") else {}
    provider_detail = components.get("official_providers", {}).get("detail", {}) if components.get("official_providers") else {}
    bridge_detail = components.get("bridge_handoff", {}).get("detail", {}) if components.get("bridge_handoff") else {}
    parity_detail = components.get("model_parity", {}).get("detail", {}) if components.get("model_parity") else {}
    alerts = classify_metals_alerts(cycle, readiness, as_of=as_of)
    return {
        "cycle_id": cycle.get("cycle_id"), "cycle_status": cycle.get("status"), "cycle_started_at_utc": cycle.get("started_at_utc"),
        "cycle_completed_at_utc": cycle.get("completed_at_utc"), "cycle_runtime_seconds": cycle.get("runtime_seconds"),
        "package_id": cycle.get("package_id"), "import_id": cycle.get("import_id"), "data_as_of_date": cycle.get("data_as_of_date"),
        "owner": cycle.get("owner"), "notification_destination": cycle.get("notification_destination"), "failed_stage": cycle.get("failed_stage"),
        "warning_count": len(cycle.get("warnings", [])), "error_count": len(cycle.get("errors", [])),
        "readiness_status": readiness.get("status"), "readiness_ready": readiness.get("ready"), "readiness_generated_at_utc": readiness.get("generated_at_utc"),
        "readiness_component_count": readiness.get("component_count"), "readiness_failed_components": ",".join(str(v) for v in readiness.get("failed_components", [])),
        "package_age_seconds": package_detail.get("age_seconds"), "package_run_status": package_detail.get("run_status"),
        "package_warning_count": package_detail.get("warning_count"), "package_error_count": package_detail.get("error_count"),
        "provider_record_count": provider_detail.get("records"), "provider_count": provider_detail.get("providers"),
        "eia_record_count": (provider_detail.get("counts") or {}).get("eia"), "world_bank_record_count": (provider_detail.get("counts") or {}).get("world_bank"),
        "bridge_surface_count": bridge_detail.get("surfaces"), "bridge_record_count": bridge_detail.get("records"),
        "model_parity_check_count": parity_detail.get("checks"),
        "registry_status": components.get("registry", {}).get("status"), "bridge_handoff_status": components.get("bridge_handoff", {}).get("status"),
        "package_status": components.get("package", {}).get("status"), "model_parity_status": components.get("model_parity", {}).get("status"),
        "vehicle_constraints_status": components.get("vehicle_constraints", {}).get("status"), "provider_status": components.get("official_providers", {}).get("status"),
        "alert_count": len(alerts), "highest_alert_severity": alerts[0].severity if alerts else "INFO", "alerts": [asdict(item) for item in alerts],
    }


def load_cycle_history(history_root: Path) -> list[dict[str, object]]:
    if not history_root.exists():
        return []
    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(history_root.glob("metals-*.json"))]
    records.sort(key=lambda item: str(item.get("started_at_utc", "")))
    return records


def project_cycle_history(records: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    rows = []
    for record in records:
        stages = record.get("stages", [])
        rows.append({"cycle_id": record.get("cycle_id"), "status": record.get("status"), "started_at_utc": record.get("started_at_utc"),
                     "completed_at_utc": record.get("completed_at_utc"), "runtime_seconds": record.get("runtime_seconds"),
                     "package_id": record.get("package_id"), "import_id": record.get("import_id"), "data_as_of_date": record.get("data_as_of_date"),
                     "failed_stage": record.get("failed_stage"), "warning_count": len(record.get("warnings", [])), "error_count": len(record.get("errors", [])),
                     "stage_count": len(stages), "passed_stage_count": sum(1 for s in stages if s.get("status") == "PASS"),
                     "failed_stage_count": sum(1 for s in stages if s.get("status") != "PASS")})
    return rows


def project_stage_history(records: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    rows = []
    for record in records:
        for ordinal, stage in enumerate(record.get("stages", []), start=1):
            rows.append({"cycle_id": record.get("cycle_id"), "cycle_status": record.get("status"), "stage_ordinal": ordinal,
                         "stage_name": stage.get("name"), "stage_status": stage.get("status"), "started_at_utc": stage.get("started_at_utc"),
                         "completed_at_utc": stage.get("completed_at_utc"), "runtime_seconds": stage.get("runtime_seconds"), "return_code": stage.get("return_code")})
    return rows


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
