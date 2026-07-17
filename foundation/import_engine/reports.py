"""Validation reporting for the Universal Import Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import csv
import json

from foundation.import_engine.integrity import PackageValidationResult
from foundation.import_engine.package import UniversalPackage


def _safe_filename(value: str) -> str:
    """Convert an identifier into a filesystem-safe filename fragment."""

    allowed = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    )

    cleaned = "".join(
        character if character in allowed else "-"
        for character in value
    )

    return cleaned.strip("-") or "package"


def write_validation_report(
    validation_root: Path,
    package: UniversalPackage,
    result: PackageValidationResult,
) -> Path:
    """Write CSV and JSON evidence for a package validation run."""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    package_fragment = _safe_filename(result.package_id)

    report_directory = (
        validation_root
        / f"{timestamp}-{package_fragment}"
    )

    report_directory.mkdir(parents=True, exist_ok=False)

    csv_path = report_directory / "file_validation_results.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "dataset_name",
            "filename",
            "required",
            "file_exists",
            "expected_row_count",
            "actual_row_count",
            "row_count_status",
            "expected_sha256",
            "calculated_sha256",
            "checksum_status",
            "validation_status",
            "error_message",
        ]

        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for file_result in result.file_results:
            writer.writerow(
                {
                    field: getattr(file_result, field)
                    for field in fieldnames
                }
            )

    summary = {
        "package_id": result.package_id,
        "platform_id": result.platform_id,
        "package_path": str(package.package_path),
        "run_id": package.identity.run_id,
        "adapter_version": package.identity.adapter_version,
        "contract_version": package.identity.contract_version,
        "generated_at_utc": package.identity.generated_at_utc,
        "manifest_sha256": result.manifest_sha256,
        "files_declared": len(result.file_results),
        "warnings": result.warning_count,
        "errors": result.error_count,
        "validation_status": "PASS" if result.passed else "FAILED",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    json_path = report_directory / "validation_summary.json"
    json_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    return report_directory