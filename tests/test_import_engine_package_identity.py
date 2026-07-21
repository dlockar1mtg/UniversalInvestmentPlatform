from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from foundation.import_engine.exceptions import (
    ManifestError,
)
from foundation.import_engine.package import (
    discover_package,
)


MANIFEST_COLUMNS = [
    "dataset_name",
    "file_name",
    "record_count",
    "sha256",
    "validation_status",
]


STATUS_COLUMNS = [
    "contract_version",
    "platform_id",
    "platform_name",
    "platform_version",
    "run_id",
    "run_started_at_utc",
    "run_completed_at_utc",
    "run_status",
    "data_as_of_date",
    "records_published",
    "warning_count",
    "error_count",
    "source_machine",
    "message",
]


def write_csv(
    path: Path,
    columns: list[str],
    rows: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def build_package(
    tmp_path: Path,
    *,
    status_adapter_version: str | None = None,
    summary_adapter_version: str | None = "1.0.0",
) -> Path:
    package_path = tmp_path / "package"
    package_path.mkdir()

    data_path = package_path / "asset_master.csv"

    data_path.write_text(
        "contract_version\n1.0.0\n",
        encoding="utf-8",
    )

    write_csv(
        package_path / "export_manifest.csv",
        MANIFEST_COLUMNS,
        [
            {
                "dataset_name": "asset_master",
                "file_name": "asset_master.csv",
                "record_count": 1,
                "sha256": "",
                "validation_status": "PASS",
            }
        ],
    )

    status_columns = list(STATUS_COLUMNS)

    if status_adapter_version is not None:
        status_columns.append(
            "adapter_version"
        )

    status_row: dict[str, object] = {
        "contract_version": "1.0.0",
        "platform_id": "crypto",
        "platform_name": (
            "Crypto Intelligence Platform"
        ),
        "platform_version": "12.0.1",
        "run_id": "crypto-run-001",
        "run_started_at_utc": (
            "2026-07-16T10:00:00Z"
        ),
        "run_completed_at_utc": (
            "2026-07-16T10:05:00Z"
        ),
        "run_status": "success",
        "data_as_of_date": "2026-07-16",
        "records_published": 1,
        "warning_count": 0,
        "error_count": 0,
        "source_machine": (
            "primary-workstation"
        ),
        "message": "Package complete.",
    }

    if status_adapter_version is not None:
        status_row["adapter_version"] = (
            status_adapter_version
        )

    write_csv(
        package_path / "platform_status.csv",
        status_columns,
        [status_row],
    )

    if summary_adapter_version is not None:
        (
            package_path
            / "package_summary.json"
        ).write_text(
            json.dumps(
                {
                    "adapter_version": (
                        summary_adapter_version
                    )
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return package_path


def test_adapter_version_falls_back_to_summary(
    tmp_path: Path,
) -> None:
    package_path = build_package(
        tmp_path,
        status_adapter_version=None,
        summary_adapter_version="1.0.0",
    )

    package = discover_package(
        package_path
    )

    assert (
        package.identity.adapter_version
        == "1.0.0"
    )


def test_platform_status_adapter_version_has_precedence(
    tmp_path: Path,
) -> None:
    package_path = build_package(
        tmp_path,
        status_adapter_version="legacy-2.0.0",
        summary_adapter_version="1.0.0",
    )

    package = discover_package(
        package_path
    )

    assert (
        package.identity.adapter_version
        == "legacy-2.0.0"
    )


def test_missing_adapter_version_remains_backward_compatible(
    tmp_path: Path,
) -> None:
    package_path = build_package(
        tmp_path,
        status_adapter_version=None,
        summary_adapter_version=None,
    )

    package = discover_package(
        package_path
    )

    assert package.identity.adapter_version == ""


def test_invalid_package_summary_is_rejected(
    tmp_path: Path,
) -> None:
    package_path = build_package(
        tmp_path,
        status_adapter_version=None,
        summary_adapter_version=None,
    )

    (
        package_path
        / "package_summary.json"
    ).write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    with pytest.raises(
        ManifestError,
        match="Unable to parse package summary",
    ):
        discover_package(
            package_path
        )