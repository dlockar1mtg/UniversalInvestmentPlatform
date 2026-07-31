from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from foundation.import_engine.exceptions import (
    DuplicatePackageError,
)
from foundation.import_engine.mtg_intake import (
    MTGPackageIntakeError,
    intake_certified_mtg_package,
    normalize_mtg_delivery,
)


REPO = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def build_package(root: Path) -> Path:
    package = root / "mtg-package"
    package.mkdir()

    asset_master = package / "asset_master.csv"
    write_csv(
        asset_master,
        [
            "universal_asset_id",
            "platform_id",
            "platform_asset_id",
            "asset_name",
            "asset_class",
            "asset_subclass",
            "currency",
            "active_flag",
        ],
        [
            {
                "universal_asset_id": "mtg:test",
                "platform_id": "mtg",
                "platform_asset_id": "test",
                "asset_name": "Test MTG Asset",
                "asset_class": "collectible",
                "asset_subclass": "mtg",
                "currency": "USD",
                "active_flag": "true",
            }
        ],
    )

    historical_performance = (
        package / "historical_performance.csv"
    )

    write_csv(
        historical_performance,
        [
            "investment_product_id",
            "universal_mtg_product_id",
            "canonical_product_name",
            "asset_class",
            "currency",
            "historical_performance_status",
            "historical_performance_eligible",
            "historical_start_date",
            "historical_end_date",
            "historical_start_value_usd",
            "historical_end_value_usd",
            "historical_elapsed_days",
            "historical_observation_count",
            "historical_distinct_dates",
            "historical_source_count",
            "historical_sources",
            "historical_total_return_pct",
            "historical_cagr_pct",
            "historical_annualized_return_pct",
            "historical_min_value_usd",
            "historical_max_value_usd",
            "historical_data_quality",
            "historical_suppression_reason",
            "forecast_eligible",
            "recommendation_eligible",
            "one_year_base_usd",
            "three_year_base_usd",
            "five_year_base_usd",
        ],
        [
            {
                "investment_product_id": "test",
                "universal_mtg_product_id": "mtg:test",
                "canonical_product_name": (
                    "Test MTG Asset"
                ),
                "asset_class": "SECRET_LAIR",
                "currency": "USD",
                "historical_performance_status": (
                    "eligible"
                ),
                "historical_performance_eligible": (
                    "true"
                ),
                "historical_start_date": "2025-07-31",
                "historical_end_date": "2026-07-31",
                "historical_start_value_usd": "100.00",
                "historical_end_value_usd": "110.00",
                "historical_elapsed_days": "365",
                "historical_observation_count": "12",
                "historical_distinct_dates": "12",
                "historical_source_count": "1",
                "historical_sources": "test",
                "historical_total_return_pct": "0.10",
                "historical_cagr_pct": "0.10",
                "historical_annualized_return_pct": (
                    "0.10"
                ),
                "historical_min_value_usd": "95.00",
                "historical_max_value_usd": "112.00",
                "historical_data_quality": "high",
                "historical_suppression_reason": "",
                "forecast_eligible": "true",
                "recommendation_eligible": "true",
                "one_year_base_usd": "110.00",
                "three_year_base_usd": "130.00",
                "five_year_base_usd": "150.00",
            }
        ],
    )

    status = package / "platform_status.csv"
    write_csv(
        status,
        [
            "platform_id",
            "run_id",
            "adapter_version",
            "contract_version",
            "generated_at_utc",
            "package_id",
            "status",
        ],
        [
            {
                "platform_id": "mtg",
                "run_id": "test-run",
                "adapter_version": "test",
                "contract_version": "v1",
                "generated_at_utc": (
                    "2026-07-31T00:00:00+00:00"
                ),
                "package_id": "mtg-test-package",
                "status": "PASS",
            }
        ],
    )

    files = {}

    for path in (
        asset_master,
        historical_performance,
        status,
    ):
        files[path.name] = {
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }

    manifest = {
        "status": "PASS",
        "delivery_contract": "uip-mtg-delivery-v1",
        "package_id": "mtg-test-package",
        "generated_at_utc": (
            "2026-07-31T00:00:00+00:00"
        ),
        "files": files,
    }

    (package / "export_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    (package / "package_summary.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    return package


def test_normalize_creates_csv_manifest_without_mutating_source(
    tmp_path: Path,
) -> None:
    source = build_package(tmp_path)
    workspace_root = tmp_path / "workspace"

    workspace, _, datasets = normalize_mtg_delivery(
        source,
        workspace_root,
    )

    assert not (
        source / "export_manifest.csv"
    ).exists()

    assert (
        workspace / "export_manifest.csv"
    ).is_file()

    assert len(datasets) == 3

    with (
        workspace / "historical_performance.csv"
    ).open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        normalized_reader = csv.DictReader(handle)
        normalized_rows = list(normalized_reader)

    assert normalized_reader.fieldnames is not None
    assert "run_id" in normalized_reader.fieldnames
    assert (
        "universal_asset_id"
        in normalized_reader.fieldnames
    )
    assert (
        "universal_mtg_product_id"
        not in normalized_reader.fieldnames
    )
    assert normalized_rows[0]["run_id"] == "test-run"
    assert (
        normalized_rows[0]["universal_asset_id"]
        == "mtg:test"
    )


def test_normalize_rejects_checksum_mismatch(
    tmp_path: Path,
) -> None:
    source = build_package(tmp_path)

    with (
        source / "asset_master.csv"
    ).open("a", encoding="utf-8") as handle:
        handle.write("\ncorruption")

    with pytest.raises(
        MTGPackageIntakeError,
        match="SHA-256 mismatch",
    ):
        normalize_mtg_delivery(
            source,
            tmp_path / "workspace",
        )


def test_intake_initializes_database_and_records_lineage(
    tmp_path: Path,
) -> None:
    source = build_package(tmp_path)
    database = tmp_path / "intake.duckdb"

    result = intake_certified_mtg_package(
        repository_root=REPO,
        source_package=source,
        database_path=database,
        workspace_root=tmp_path / "workspace",
        validation_root=tmp_path / "validation",
        result_root=tmp_path / "results",
    )

    assert result.intake_status == "PASS"
    assert result.import_status == "IMPORTED"
    assert result.imported_row_count == 3
    assert "historical_performance" in (
        result.imported_datasets
    )
    assert Path(result.result_path).is_file()

    connection = duckdb.connect(
        str(database),
        read_only=True,
    )

    try:
        objects = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                """
            ).fetchall()
        }

        assert (
            "historical_performance_history"
            in objects
        )

        package_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM universal_packages
            WHERE package_id = 'mtg-test-package'
            """
        ).fetchone()[0]

        lineage_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM asset_master_history
            WHERE _package_id = 'mtg-test-package'
            """
        ).fetchone()[0]

        historical_lineage_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM historical_performance_history
            WHERE _package_id = 'mtg-test-package'
            """
        ).fetchone()[0]
    finally:
        connection.close()

    assert package_count == 1
    assert lineage_count == 1
    assert historical_lineage_count == 1


def test_duplicate_package_is_rejected(
    tmp_path: Path,
) -> None:
    source = build_package(tmp_path)
    database = tmp_path / "intake.duckdb"

    arguments = {
        "repository_root": REPO,
        "source_package": source,
        "database_path": database,
        "workspace_root": tmp_path / "workspace",
        "validation_root": tmp_path / "validation",
        "result_root": tmp_path / "results",
    }

    intake_certified_mtg_package(**arguments)

    with pytest.raises(DuplicatePackageError):
        intake_certified_mtg_package(**arguments)

def test_historical_performance_is_registered_for_import() -> None:
    from foundation.import_engine.loader import (
        SUPPORTED_DATASETS,
    )

    assert SUPPORTED_DATASETS[
        "historical_performance"
    ] == "historical_performance_history"

def test_native_history_accepts_platform_status_aliases(
    tmp_path: Path,
) -> None:
    source = build_package(tmp_path)

    status_path = source / "platform_status.csv"

    write_csv(
        status_path,
        [
            "platform",
            "platform_run_id",
            "adapter_version",
            "contract_version",
            "run_completed_at_utc",
            "package_id",
            "status",
        ],
        [
            {
                "platform": "MTG",
                "platform_run_id": "alias-run",
                "adapter_version": "alias-adapter",
                "contract_version": "1.0.0",
                "run_completed_at_utc": (
                    "2026-07-31T00:00:00+00:00"
                ),
                "package_id": "mtg-test-package",
                "status": "PASS",
            }
        ],
    )

    manifest_path = source / "export_manifest.json"
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    manifest["files"]["platform_status.csv"] = {
        "sha256": sha256(status_path),
        "size_bytes": status_path.stat().st_size,
    }

    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    workspace, _, _ = normalize_mtg_delivery(
        source,
        tmp_path / "workspace",
    )

    with (
        workspace / "historical_performance.csv"
    ).open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        row = next(csv.DictReader(handle))

    assert row["platform_id"] == "MTG"
    assert row["run_id"] == "alias-run"
    assert (
        row["generated_at_utc"]
        == "2026-07-31T00:00:00+00:00"
    )

def test_native_history_uses_package_id_when_run_id_missing(
    tmp_path: Path,
) -> None:
    source = build_package(tmp_path)

    status_path = source / "platform_status.csv"

    write_csv(
        status_path,
        [
            "platform",
            "status",
            "interface_name",
            "contract_version",
            "products",
            "forecast_eligible",
            "recommendation_eligible",
            "diagnostics",
            "generated_at_utc",
        ],
        [
            {
                "platform": "MTG",
                "status": "PASS",
                "interface_name": (
                    "mtg-hosted-uip-delivery-v1"
                ),
                "contract_version": "1",
                "products": "1",
                "forecast_eligible": "1",
                "recommendation_eligible": "1",
                "diagnostics": "0",
                "generated_at_utc": (
                    "2026-07-31T00:00:00+00:00"
                ),
            }
        ],
    )

    manifest_path = source / "export_manifest.json"
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    manifest["files"]["platform_status.csv"] = {
        "sha256": sha256(status_path),
        "size_bytes": status_path.stat().st_size,
    }

    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    workspace, _, _ = normalize_mtg_delivery(
        source,
        tmp_path / "workspace",
    )

    with (
        workspace / "historical_performance.csv"
    ).open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        row = next(csv.DictReader(handle))

    assert row["platform_id"] == "MTG"
    assert row["run_id"] == "mtg-test-package"
    assert (
        row["model_version"]
        == "mtg-hosted-uip-delivery-v1"
    )
