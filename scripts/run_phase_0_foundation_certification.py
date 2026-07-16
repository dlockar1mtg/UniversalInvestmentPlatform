from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT
    / "data"
    / "validation"
    / "phase_0_foundation_certification.json"
)


CHECKS = [
    ("environment", "check_environment.py"),
    ("contracts", "run_phase_0_3_validation.py"),
    ("registry", "run_phase_0_4_validation.py"),
    ("integration_smoke_test", "run_phase_0_5_smoke_test.py"),
    ("integration_database", "validate_integration_db.py"),
    ("cross_contracts", "validate_cross_contracts.py"),
    ("freshness", "validate_freshness.py"),
    ("manifests", "validate_manifests.py"),
]


def run_check(name: str, script_name: str) -> dict[str, Any]:
    script_path = ROOT / "scripts" / script_name

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    print(f"\n{name}")
    print("=" * 72)

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)

    return {
        "name": name,
        "script": script_name,
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    results = [
        run_check(name, script)
        for name, script in CHECKS
    ]

    passed_count = sum(
        1 for result in results if result["passed"]
    )

    failed_count = len(results) - passed_count
    certified = failed_count == 0

    payload = {
        "certification_version": "1.0.0",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "certified": certified,
        "checks_total": len(results),
        "checks_passed": passed_count,
        "checks_failed": failed_count,
        "results": results,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nPhase 0 Foundation Certification")
    print("=" * 72)
    print(f"Checks passed: {passed_count}")
    print(f"Checks failed: {failed_count}")
    print(f"Certified: {certified}")
    print(f"Report: {REPORT_PATH}")

    return 0 if certified else 1


if __name__ == "__main__":
    raise SystemExit(main())