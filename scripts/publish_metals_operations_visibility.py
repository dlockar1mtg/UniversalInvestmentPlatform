"""Publish current and historical Metals operations visibility datasets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_operations_visibility import (  # noqa: E402
    build_metals_operations_snapshot,
    load_cycle_history,
    project_cycle_history,
    project_stage_history,
    write_csv,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish Metals operations visibility datasets.")
    parser.add_argument(
        "--operations-root",
        type=Path,
        default=ROOT / "data" / "operations" / "metals",
    )
    args = parser.parse_args()
    operations_root = args.operations_root.resolve()
    cycle_path = operations_root / "cycle_history" / "latest.json"
    readiness_path = operations_root / "latest_readiness.json"
    if not cycle_path.exists() or not readiness_path.exists():
        print("METALS OPERATIONS VISIBILITY: FAILED")
        print("Latest cycle and readiness evidence are required.")
        return 1

    cycle = json.loads(cycle_path.read_text(encoding="utf-8"))
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    snapshot = build_metals_operations_snapshot(cycle, readiness)
    history = load_cycle_history(operations_root / "cycle_history")
    cycle_rows = project_cycle_history(history)
    stage_rows = project_stage_history(history)

    write_json(operations_root / "visibility" / "current_snapshot.json", snapshot)
    write_csv(operations_root / "visibility" / "current_snapshot.csv", [{k: v for k, v in snapshot.items() if k != "alerts"}])
    write_json(operations_root / "visibility" / "alerts.json", snapshot["alerts"])
    write_csv(operations_root / "visibility" / "alerts.csv", list(snapshot["alerts"]))
    write_csv(operations_root / "visibility" / "cycle_history.csv", cycle_rows)
    write_csv(operations_root / "visibility" / "stage_history.csv", stage_rows)

    print("METALS OPERATIONS VISIBILITY: PASS")
    print(f"Cycle rows: {len(cycle_rows)}")
    print(f"Stage rows: {len(stage_rows)}")
    print(f"Alerts: {snapshot['alert_count']}")
    print(f"Highest severity: {snapshot['highest_alert_severity']}")
    return 0 if snapshot["highest_alert_severity"] != "CRITICAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
