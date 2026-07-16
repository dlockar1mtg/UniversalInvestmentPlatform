from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "integration" / "uiip_integration.duckdb"
SETTINGS_PATH = ROOT / "config" / "validation" / "validation_settings.json"
REPORT_PATH = ROOT / "data" / "validation" / "phase_0_6_manifest_validation.json"

sys.path.insert(0, str(ROOT))

from validation.findings import (  # noqa: E402
    ValidationFinding,
    has_failures,
    severity_counts,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> int:
    if not DATABASE_PATH.exists():
        print("Integration database does not exist.", file=sys.stderr)
        return 2

    settings = json.loads(
        SETTINGS_PATH.read_text(encoding="utf-8")
    )

    findings: list[ValidationFinding] = []

    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT
                platform_id,
                run_id,
                export_name,
                file_name,
                file_format,
                record_count,
                file_size_bytes,
                sha256,
                validation_status
            FROM contracts.export_manifest
            """
        ).fetchall()

    if not rows:
        findings.append(
            ValidationFinding(
                validation_id="MANIFEST-INFO-001",
                category="manifest",
                severity="info",
                message=(
                    "No export-manifest records are currently imported."
                ),
                suggested_action=(
                    "This is acceptable during Phase 0 testing."
                ),
            )
        )

    for (
        platform_id,
        run_id,
        export_name,
        file_name,
        file_format,
        record_count,
        file_size_bytes,
        expected_hash,
        validation_status,
    ) in rows:
        exchange_path = ROOT / "exchange" / platform_id / file_name

        if not exchange_path.exists():
            findings.append(
                ValidationFinding(
                    validation_id="MANIFEST-FILE-001",
                    category="manifest",
                    severity="error",
                    platform_id=platform_id,
                    run_id=run_id,
                    contract_name=export_name,
                    record_identifier=file_name,
                    message="Manifest file does not exist.",
                    suggested_action=(
                        "Republish the export or correct the manifest path."
                    ),
                )
            )
            continue

        actual_size = exchange_path.stat().st_size

        if (
            file_size_bytes is not None
            and actual_size != file_size_bytes
        ):
            findings.append(
                ValidationFinding(
                    validation_id="MANIFEST-SIZE-001",
                    category="manifest",
                    severity="error",
                    platform_id=platform_id,
                    run_id=run_id,
                    contract_name=export_name,
                    record_identifier=file_name,
                    message=(
                        f"File size mismatch: expected "
                        f"{file_size_bytes}, found {actual_size}."
                    ),
                    suggested_action="Regenerate the manifest.",
                )
            )

        if expected_hash:
            actual_hash = sha256_file(exchange_path)

            if actual_hash.lower() != expected_hash.lower():
                findings.append(
                    ValidationFinding(
                        validation_id="MANIFEST-HASH-001",
                        category="manifest",
                        severity="error",
                        platform_id=platform_id,
                        run_id=run_id,
                        contract_name=export_name,
                        record_identifier=file_name,
                        message="SHA-256 checksum mismatch.",
                        suggested_action=(
                            "Reject the package and republish the export."
                        ),
                    )
                )
        elif settings["manifest"][
            "allow_missing_checksum_before_production"
        ]:
            findings.append(
                ValidationFinding(
                    validation_id="MANIFEST-HASH-WARN-001",
                    category="manifest",
                    severity="warning",
                    platform_id=platform_id,
                    run_id=run_id,
                    contract_name=export_name,
                    record_identifier=file_name,
                    message="Manifest checksum is not populated.",
                    suggested_action=(
                        "Populate SHA-256 before production use."
                    ),
                )
            )

        if validation_status == "invalid":
            findings.append(
                ValidationFinding(
                    validation_id="MANIFEST-STATUS-001",
                    category="manifest",
                    severity="error",
                    platform_id=platform_id,
                    run_id=run_id,
                    contract_name=export_name,
                    record_identifier=file_name,
                    message=(
                        "Manifest marks the export as invalid."
                    ),
                    suggested_action=(
                        "Do not import until validation succeeds."
                    ),
                )
            )

    counts = severity_counts(findings)

    payload = {
        "validation_version": "1.0.0",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "valid": not has_failures(findings),
        "severity_counts": counts,
        "findings": [finding.to_dict() for finding in findings],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Manifest validation")
    print("=" * 72)
    print(f"Info findings: {counts['info']}")
    print(f"Warnings: {counts['warning']}")
    print(f"Errors: {counts['error']}")
    print(f"Critical findings: {counts['critical']}")

    for finding in findings:
        print(
            f"{finding.severity.upper()}: "
            f"{finding.validation_id} — {finding.message}"
        )

    return 1 if has_failures(findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())