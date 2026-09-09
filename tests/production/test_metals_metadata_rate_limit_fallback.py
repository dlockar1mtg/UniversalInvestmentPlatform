from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_metals_production_workflow_limits_fallback_to_rate_limit() -> None:
    workflow = (ROOT / ".github" / "workflows" / "metals-production-cycle.yml").read_text(encoding="utf-8")
    assert "YFRateLimitError|Too Many Requests|Rate limited" in workflow
    assert "validate_metals_vehicle_metadata_fallback.py" in workflow
    assert "non-rate-limit reason" in workflow


def test_existing_metadata_is_valid_while_aging() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_metals_vehicle_metadata_fallback.py"),
            "--as-of",
            "2026-09-09",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"AGING": 11' in result.stdout
    assert '"status": "METALS_VEHICLE_METADATA_FALLBACK_PASS"' in result.stdout


def test_existing_metadata_fails_closed_once_stale() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_metals_vehicle_metadata_fallback.py"),
            "--as-of",
            "2026-10-24",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert '"STALE": 11' in result.stdout
    assert '"status": "FAIL_CLOSED"' in result.stdout
