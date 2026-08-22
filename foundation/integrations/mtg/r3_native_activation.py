"""R3 MTG production-activation binding over the certified A2 native package.

A2 intentionally certified the 968-row native MTG authority. Its package builder also
writes ``platform_status.csv``, but the historical A2 manifest registered only the
native-authority dataset, so that status file was not transactionally imported.

R3 needs a complete current-authority cutover. This wrapper leaves A2 certification
semantics untouched, adds the already-generated status file to the package manifest,
then imports 968 native rows plus exactly one platform-status row. No generic MTG
forecast, recommendation, or risk authority is created.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.loader import ImportResult, import_package
from foundation.integrations.mtg.v1_integration_binding import (
    DATASET_NAME,
    MANIFEST_FILENAME,
    PLATFORM_STATUS_FILENAME,
    MTGV1IntegrationError,
    build_mtg_v1_integration_package,
)


PLATFORM_STATUS_DATASET_NAME = "platform_status"
NATIVE_ADAPTER_VERSION = "mtg-v1-native-authority-binding-1.0.0"


@dataclass(frozen=True)
class MTGR3ActivationResult:
    status: str
    package_id: str
    import_id: str
    import_status: str
    payload_sha256: str
    native_payload_rows: int
    package_imported_row_count: int
    native_history_row_count: int
    native_current_row_count: int
    platform_status_history_row_count: int
    platform_status_current_row_count: int
    platform_status_current_platform_id: str
    platform_status_current_adapter_version: str
    generic_asset_current_rows: int
    generic_forecast_current_rows: int
    generic_recommendation_current_rows: int
    generic_risk_current_rows: int
    lineage_missing_rows: int
    activation_certified: bool


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def _build_config(
    *,
    repository_root: Path,
    database_path: Path,
    validation_root: Path,
) -> ImportEngineConfig:
    repository = repository_root.resolve()
    return ImportEngineConfig(
        repository_root=repository,
        database_path=database_path.resolve(),
        schema_root=repository / "schemas" / "v1" / "csv",
        integration_root=repository / "data" / "integration",
        validation_root=validation_root.resolve(),
    )


def _register_platform_status(package_path: Path) -> None:
    """Register the A2-generated platform status without altering its bytes."""

    manifest_path = package_path / MANIFEST_FILENAME
    status_path = package_path / PLATFORM_STATUS_FILENAME

    if not manifest_path.is_file():
        raise MTGV1IntegrationError("A2 integration manifest is missing.")

    if not status_path.is_file():
        raise MTGV1IntegrationError("A2-generated platform_status.csv is missing.")

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    expected_fields = [
        "dataset_name",
        "filename",
        "row_count",
        "sha256",
        "required",
        "validation_status",
    ]

    if fieldnames != expected_fields:
        raise MTGV1IntegrationError(
            "A2 integration manifest fields changed before R3 activation."
        )

    dataset_names = [str(row.get("dataset_name", "")).strip() for row in rows]

    if dataset_names != [DATASET_NAME]:
        raise MTGV1IntegrationError(
            "A2 integration manifest must contain only the certified native dataset "
            "before R3 status registration."
        )

    status_sha = _sha256(status_path)

    rows.append(
        {
            "dataset_name": PLATFORM_STATUS_DATASET_NAME,
            "filename": PLATFORM_STATUS_FILENAME,
            "row_count": "1",
            "sha256": status_sha,
            "required": "true",
            "validation_status": "PASS",
        }
    )

    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=expected_fields)
        writer.writeheader()
        writer.writerows(rows)


def activate_mtg_v1_authority_for_r3(
    *,
    repository_root: Path,
    payload_path: Path,
    manifest_path: Path,
    schema_contract_path: Path,
    export_contract_path: Path,
    portability_correction_path: Path,
    database_path: Path,
    workspace_root: Path,
    validation_root: Path,
) -> MTGR3ActivationResult:
    """Activate certified native MTG authority plus its canonical status row."""

    package_path, acceptance = build_mtg_v1_integration_package(
        payload_path=payload_path,
        manifest_path=manifest_path,
        schema_contract_path=schema_contract_path,
        export_contract_path=export_contract_path,
        portability_correction_path=portability_correction_path,
        workspace_root=workspace_root,
    )

    _register_platform_status(package_path)

    config = _build_config(
        repository_root=repository_root,
        database_path=database_path,
        validation_root=validation_root,
    )

    initialize_database(config)

    import_result: ImportResult = import_package(
        config=config,
        package_path=package_path,
        force=False,
    )

    expected_package_rows = acceptance.payload_rows + 1

    if import_result.imported_row_count != expected_package_rows:
        raise MTGV1IntegrationError(
            "R3 MTG package must import native payload rows plus exactly one "
            "platform-status row."
        )

    connection = duckdb.connect(str(database_path.resolve()), read_only=True)

    try:
        package_id = import_result.package_id

        native_history = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                """,
                [package_id],
            ).fetchone()[0]
        )

        native_current = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_current
                WHERE _package_id = ?
                """,
                [package_id],
            ).fetchone()[0]
        )

        status_history = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM platform_status_history
                WHERE _package_id = ?
                  AND lower(platform_id) = 'mtg'
                """,
                [package_id],
            ).fetchone()[0]
        )

        status_rows = connection.execute(
            """
            SELECT platform_id, adapter_version, _package_id, _import_id
            FROM platform_status_current
            WHERE lower(platform_id) = 'mtg'
            """
        ).fetchall()

        generic_counts = {}
        for table in (
            "asset_master_current",
            "forecasts_current",
            "recommendations_current",
            "risk_metrics_current",
        ):
            generic_counts[table] = int(
                connection.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE lower(platform_id) = 'mtg'
                    """
                ).fetchone()[0]
            )

        lineage_missing = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                  AND (
                      _import_id IS NULL
                      OR _package_id IS NULL
                      OR _source_platform IS NULL
                      OR _source_filename IS NULL
                      OR _source_row_number IS NULL
                      OR _manifest_sha256 IS NULL
                      OR _imported_at_utc IS NULL
                  )
                """,
                [package_id],
            ).fetchone()[0]
        )
    finally:
        connection.close()

    if native_history != acceptance.payload_rows:
        raise MTGV1IntegrationError("R3 native MTG history row count changed.")

    if native_current != acceptance.payload_rows:
        raise MTGV1IntegrationError("R3 native MTG current row count changed.")

    if status_history != 1:
        raise MTGV1IntegrationError(
            "R3 MTG activation did not import exactly one platform-status row."
        )

    if len(status_rows) != 1:
        raise MTGV1IntegrationError(
            "R3 MTG current status must reconcile to exactly one row."
        )

    current_platform_id, current_adapter, current_package, current_import = status_rows[0]

    if current_platform_id != "mtg":
        raise MTGV1IntegrationError(
            "R3 MTG current status did not transition to canonical lower-case ID."
        )

    if current_adapter != NATIVE_ADAPTER_VERSION:
        raise MTGV1IntegrationError("R3 MTG current status adapter is not native A2.")

    if current_package != import_result.package_id:
        raise MTGV1IntegrationError("R3 MTG current status package lineage changed.")

    if current_import != import_result.import_id:
        raise MTGV1IntegrationError("R3 MTG current status import lineage changed.")

    if any(generic_counts.values()):
        raise MTGV1IntegrationError(
            "Legacy generic MTG analytical rows remain current after native activation."
        )

    if lineage_missing != 0:
        raise MTGV1IntegrationError("R3 native MTG rows are missing UIP lineage.")

    return MTGR3ActivationResult(
        status="UIP_R3_MTG_NATIVE_AUTHORITY_ACTIVATION_PASS",
        package_id=import_result.package_id,
        import_id=import_result.import_id,
        import_status=import_result.status,
        payload_sha256=acceptance.payload_sha256,
        native_payload_rows=acceptance.payload_rows,
        package_imported_row_count=import_result.imported_row_count,
        native_history_row_count=native_history,
        native_current_row_count=native_current,
        platform_status_history_row_count=status_history,
        platform_status_current_row_count=len(status_rows),
        platform_status_current_platform_id=current_platform_id,
        platform_status_current_adapter_version=current_adapter,
        generic_asset_current_rows=generic_counts["asset_master_current"],
        generic_forecast_current_rows=generic_counts["forecasts_current"],
        generic_recommendation_current_rows=generic_counts[
            "recommendations_current"
        ],
        generic_risk_current_rows=generic_counts["risk_metrics_current"],
        lineage_missing_rows=lineage_missing,
        activation_certified=True,
    )


def result_to_dict(result: MTGR3ActivationResult) -> dict[str, object]:
    """Return a stable JSON-serializable activation result."""

    return asdict(result)
