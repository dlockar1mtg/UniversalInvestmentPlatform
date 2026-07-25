from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from foundation.production.metals_operations_visibility import (
    build_metals_operations_snapshot,
    classify_metals_alerts,
    load_cycle_history,
    project_cycle_history,
    project_stage_history,
    write_csv,
    write_json,
)


def _cycle(**overrides):
    document = {
        "cycle_id": "metals-cycle-1",
        "status": "PASS",
        "started_at_utc": "2026-07-25T14:00:00+00:00",
        "completed_at_utc": "2026-07-25T14:00:04+00:00",
        "runtime_seconds": 4.0,
        "package_id": "metals-package-1",
        "import_id": "3cd57757-5df1-4366-9952-a116e8ac1c43",
        "data_as_of_date": "2026-07-25T14:00:00+00:00",
        "owner": "owner",
        "notification_destination": "console",
        "failed_stage": None,
        "warnings": [],
        "errors": [],
        "stages": [
            {"name": "export", "status": "PASS", "started_at_utc": "2026-07-25T14:00:00+00:00", "completed_at_utc": "2026-07-25T14:00:01+00:00", "runtime_seconds": 1.0, "return_code": 0},
            {"name": "readiness", "status": "PASS", "started_at_utc": "2026-07-25T14:00:01+00:00", "completed_at_utc": "2026-07-25T14:00:04+00:00", "runtime_seconds": 3.0, "return_code": 0},
        ],
    }
    document.update(overrides)
    return document


def _readiness(package_age=2, status="PASS"):
    components = []
    for name in ("registry", "bridge_handoff", "model_parity", "vehicle_constraints"):
        detail = {"records": 38, "surfaces": 5} if name == "bridge_handoff" else {"checks": 9} if name == "model_parity" else {}
        components.append({"name": name, "status": status, "detail": detail})
    components.append({"name": "package", "status": status, "detail": {"age_seconds": package_age, "run_status": "SUCCESS", "warning_count": 0, "error_count": 0}})
    components.append({"name": "official_providers", "status": status, "detail": {"providers": 2, "records": 9, "counts": {"eia": 1, "world_bank": 8}}})
    return {"status": status, "ready": status == "PASS", "generated_at_utc": "2026-07-25T14:00:04+00:00", "component_count": 6, "failed_components": [] if status == "PASS" else ["package"], "components": components}


def test_healthy_snapshot_has_no_alerts() -> None:
    snapshot = build_metals_operations_snapshot(_cycle(), _readiness(), as_of=datetime(2026, 7, 25, 15, tzinfo=timezone.utc))
    assert snapshot["highest_alert_severity"] == "INFO"
    assert snapshot["alert_count"] == 0
    assert snapshot["import_id"]
    assert snapshot["provider_record_count"] == 9
    assert snapshot["model_parity_check_count"] == 9


def test_stale_package_is_critical() -> None:
    alerts = classify_metals_alerts(_cycle(), _readiness(package_age=4_000_000), as_of=datetime(2026, 7, 25, 15, tzinfo=timezone.utc))
    assert any(item.code == "PACKAGE_STALE" and item.severity == "CRITICAL" for item in alerts)


def test_missing_import_and_failed_readiness_are_critical() -> None:
    alerts = classify_metals_alerts(_cycle(import_id=None), _readiness(status="FAILED"), as_of=datetime(2026, 7, 25, 15, tzinfo=timezone.utc))
    codes = {item.code for item in alerts}
    assert "IMPORT_ID_MISSING" in codes
    assert "READINESS_FAILED" in codes
    assert "COMPONENT_FAILED" in codes


def test_history_projection_and_writers(tmp_path: Path) -> None:
    history_root = tmp_path / "history"
    history_root.mkdir()
    write_json(history_root / "metals-cycle-1.json", _cycle())
    write_json(history_root / "latest.json", _cycle())
    records = load_cycle_history(history_root)
    cycles = project_cycle_history(records)
    stages = project_stage_history(records)
    assert len(records) == 1
    assert cycles[0]["passed_stage_count"] == 2
    assert len(stages) == 2
    write_csv(tmp_path / "cycles.csv", cycles)
    assert (tmp_path / "cycles.csv").read_text(encoding="utf-8").startswith("cycle_id,")
