from __future__ import annotations

import csv
import json
from pathlib import Path

from foundation.production.metals_operations_status import (
    build_metals_operations_status,
    write_metals_operations_status,
)


def test_operations_status_combines_cycle_and_readiness(tmp_path: Path) -> None:
    cycle_path = tmp_path / "latest.json"
    readiness_path = tmp_path / "latest_readiness.json"
    cycle_path.write_text(
        json.dumps(
            {
                "cycle_id": "metals-cycle-1",
                "status": "PASS",
                "package_id": "package-1",
                "owner": "Devon Lockard",
                "warnings": [],
                "errors": [],
            }
        ),
        encoding="utf-8",
    )
    readiness_path.write_text(
        json.dumps(
            {
                "status": "PASS",
                "component_count": 2,
                "failed_components": [],
                "components": [
                    {"name": "official_providers", "status": "PASS"},
                    {"name": "package", "status": "PASS"},
                ],
            }
        ),
        encoding="utf-8",
    )

    status = build_metals_operations_status(
        latest_cycle_path=cycle_path,
        latest_readiness_path=readiness_path,
    )
    assert status["cycle_status"] == "PASS"
    assert status["readiness_status"] == "PASS"
    assert status["provider_status"] == "PASS"
    assert status["package_id"] == "package-1"

    json_path, csv_path = write_metals_operations_status(status, tmp_path / "output")
    assert json_path.exists()
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["cycle_id"] == "metals-cycle-1"
