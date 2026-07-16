from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "integration" / "uiip_integration.duckdb"
SETTINGS_PATH = ROOT / "config" / "validation" / "validation_settings.json"
REPORT_PATH = ROOT / "data" / "validation" / "phase_0_6_freshness_validation.json"

sys.path.insert(0, str(ROOT))

from validation.findings import (  # noqa: E402
    ValidationFinding,
    has_failures,
    severity_counts,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_settings() -> dict:
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def main() -> int:
    if not DATABASE_PATH.exists():
        print("Integration database does not exist.", file=sys.stderr)
        return 2

    settings = load_settings()
    warning_multiplier = settings["freshness"]["warning_multiplier"]
    error_multiplier = settings["freshness"]["error_multiplier"]

    findings: list[ValidationFinding] = []
    now = utc_now()

    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT
                platform_id,
                platform_name,
                platform_status,
                integration_stage,
                expected_refresh_frequency,
                freshness_threshold_hours,
                last_successful_run_at_utc,
                is_enabled
            FROM registry.platforms
            ORDER BY platform_id
            """
        ).fetchall()

    for (
        platform_id,
        platform_name,
        platform_status,
        integration_stage,
        refresh_frequency,
        threshold_hours,
        last_run,
        is_enabled,
    ) in rows:
        if not is_enabled:
            findings.append(
                ValidationFinding(
                    validation_id="FRESHNESS-INFO-001",
                    category="freshness",
                    severity="info",
                    platform_id=platform_id,
                    message=(
                        f"{platform_name} is disabled in the registry."
                    ),
                    suggested_action="No action required.",
                )
            )
            continue

        if refresh_frequency == "not_applicable":
            continue

        if threshold_hours is None:
            findings.append(
                ValidationFinding(
                    validation_id="FRESHNESS-WARN-001",
                    category="freshness",
                    severity="warning",
                    platform_id=platform_id,
                    message=(
                        "No freshness threshold is configured."
                    ),
                    suggested_action=(
                        "Set freshness_threshold_hours in the registry."
                    ),
                )
            )
            continue

        if last_run is None:
            severity = "warning"

            if integration_stage in {
                "integrated",
                "validated",
                "production",
            }:
                severity = "error"

            findings.append(
                ValidationFinding(
                    validation_id="FRESHNESS-MISSING-001",
                    category="freshness",
                    severity=severity,
                    platform_id=platform_id,
                    message=(
                        "No successful-run timestamp is available."
                    ),
                    suggested_action=(
                        "Publish a successful platform-status record "
                        "or update the registry."
                    ),
                )
            )
            continue

        last_run_utc = last_run.replace(tzinfo=timezone.utc)
        age_hours = (now - last_run_utc).total_seconds() / 3600

        warning_limit = threshold_hours * warning_multiplier
        error_limit = threshold_hours * error_multiplier

        if age_hours > error_limit:
            findings.append(
                ValidationFinding(
                    validation_id="FRESHNESS-ERROR-001",
                    category="freshness",
                    severity="error",
                    platform_id=platform_id,
                    message=(
                        f"Last successful run is {age_hours:.1f} hours old, "
                        f"beyond the error threshold of "
                        f"{error_limit:.1f} hours."
                    ),
                    suggested_action="Run or refresh the platform.",
                )
            )
        elif age_hours > warning_limit:
            findings.append(
                ValidationFinding(
                    validation_id="FRESHNESS-WARN-002",
                    category="freshness",
                    severity="warning",
                    platform_id=platform_id,
                    message=(
                        f"Last successful run is {age_hours:.1f} hours old, "
                        f"beyond the warning threshold of "
                        f"{warning_limit:.1f} hours."
                    ),
                    suggested_action="Review platform freshness.",
                )
            )

    counts = severity_counts(findings)

    payload = {
        "validation_version": "1.0.0",
        "generated_at_utc": now.isoformat(),
        "valid": not has_failures(findings),
        "severity_counts": counts,
        "findings": [finding.to_dict() for finding in findings],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Freshness validation")
    print("=" * 72)
    print(f"Info findings: {counts['info']}")
    print(f"Warnings: {counts['warning']}")
    print(f"Errors: {counts['error']}")
    print(f"Critical findings: {counts['critical']}")

    for finding in findings:
        print(
            f"{finding.severity.upper()}: "
            f"{finding.platform_id} — {finding.message}"
        )

    return 1 if has_failures(findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())