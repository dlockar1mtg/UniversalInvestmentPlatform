from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_metals_production_workflow_bounds_provider_degradation_fallback() -> None:
    workflow = (ROOT / ".github" / "workflows" / "metals-production-cycle.yml").read_text(encoding="utf-8")
    assert "--output \"$candidate\"" in workflow
    assert "cp \"$candidate\" config/metals/vehicle_market_metadata.csv" in workflow
    assert "YFRateLimitError|Too Many Requests|Rate limited" in workflow
    assert "METALS VEHICLE METADATA COLLECTION: PARTIAL" in workflow
    assert "YAHOO_RATE_LIMIT" in workflow
    assert "YAHOO_INCOMPLETE_METADATA_RESPONSE" in workflow
    assert "validate_metals_vehicle_metadata_fallback.py" in workflow
    assert "unapproved reason" in workflow


def test_existing_metadata_is_valid_while_aging() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_metals_vehicle_metadata_fallback.py"),
            "--as-of",
            "2026-09-09",
            "--fallback-reason",
            "YAHOO_INCOMPLETE_METADATA_RESPONSE",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    # PASS already requires every vehicle complete with none STALE or MISSING; the
    # number of AGING rows depends on how many vehicles are registered.
    assert '"fallback_reason": "YAHOO_INCOMPLETE_METADATA_RESPONSE"' in result.stdout
    assert '"status": "METALS_VEHICLE_METADATA_FALLBACK_PASS"' in result.stdout


def test_existing_metadata_fails_closed_once_stale() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_metals_vehicle_metadata_fallback.py"),
            "--as-of",
            "2026-10-24",
            "--fallback-reason",
            "YAHOO_RATE_LIMIT",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert '"STALE": 11' in result.stdout
    assert '"status": "FAIL_CLOSED"' in result.stdout


def test_unapproved_fallback_reason_is_rejected() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_metals_vehicle_metadata_fallback.py"),
            "--fallback-reason",
            "GENERIC_NETWORK_FAILURE",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
