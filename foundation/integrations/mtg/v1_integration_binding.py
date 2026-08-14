"""UIP-MTG-A2 canonical integration binding for certified MTG V1 authority."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.loader import ImportResult, import_package
from foundation.integrations.mtg.v1_export_acceptance import (
    MTGV1AcceptanceResult,
    accept_mtg_v1_export,
)


DATASET_NAME = "mtg_native_authority"
DATASET_FILENAME = "mtg_native_authority.csv"
MANIFEST_FILENAME = "export_manifest.csv"
PLATFORM_STATUS_FILENAME = "platform_status.csv"

NATIVE_FIELDS = (
    "mtg_asset_id",
    "mtg_lane",
    "native_asset_id",
    "product_name",
    "lane_authority_state",
    "current_price_usd",
    "current_price_authority_available",
    "forecast_authority_available",
    "forecast_1y_price_usd",
    "forecast_1y_return",
    "risk_authority_available",
    "native_rank",
    "native_rank_type",
    "native_purchase_status",
    "purchase_semantic",
    "evidence_state",
    "actionability_state",
    "execution_ready_purchase_certified",
    "manual_execution_price_check_required",
    "native_authority_pointer",
    "native_authority_sha256",
    "snapshot_population_is_permanent",
    "automatic_purchase_execution",
)

BOOLEAN_FIELDS = (
    "current_price_authority_available",
    "forecast_authority_available",
    "risk_authority_available",
    "execution_ready_purchase_certified",
    "manual_execution_price_check_required",
    "snapshot_population_is_permanent",
    "automatic_purchase_execution",
)


class MTGV1IntegrationError(RuntimeError):
    """Certified MTG V1 authority could not be integrated losslessly."""


@dataclass(frozen=True)
class MTGV1IntegrationResult:
    status: str
    package_id: str
    import_id: str
    import_status: str
    payload_sha256: str
    payload_rows: int
    imported_row_count: int
    history_row_count: int
    current_row_count: int
    field_count: int
    lane_counts: dict[str, int]
    null_value_counts: dict[str, int]
    duplicate_mtg_asset_ids: int
    secret_lair_buy_candidate_rows: int
    secret_lair_buy_semantic_mismatches: int
    secret_lair_buy_manual_check_failures: int
    execution_ready_true_rows: int
    automatic_execution_true_rows: int
    lineage_missing_rows: int
    native_fields_preserved: bool
    cross_asset_rank_created: bool
    generic_recommendation_created: bool
    generic_forecast_created: bool
    generic_risk_created: bool
    uip_integration_certified: bool


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def _read_payload(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise MTGV1IntegrationError("MTG payload has no CSV header.")
        fields = [str(value).strip() for value in reader.fieldnames]
        rows = [
            {
                str(key).strip(): "" if value is None else str(value).strip()
                for key, value in row.items()
                if key is not None
            }
            for row in reader
            if any(str(value or "").strip() for value in row.values())
        ]
    return fields, rows


def _write_manifest(
    *,
    package_path: Path,
    row_count: int,
    payload_sha256: str,
) -> None:
    manifest_path = package_path / MANIFEST_FILENAME
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "dataset_name",
                "filename",
                "row_count",
                "sha256",
                "required",
                "validation_status",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "dataset_name": DATASET_NAME,
                "filename": DATASET_FILENAME,
                "row_count": row_count,
                "sha256": payload_sha256,
                "required": "true",
                "validation_status": "PASS",
            }
        )


def _write_platform_status(
    *,
    package_path: Path,
    package_id: str,
    run_id: str,
) -> None:
    status_path = package_path / PLATFORM_STATUS_FILENAME
    with status_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "package_id",
                "platform_id",
                "run_id",
                "adapter_version",
                "contract_version",
                "generated_at_utc",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "package_id": package_id,
                "platform_id": "mtg",
                "run_id": run_id,
                "adapter_version": "mtg-v1-native-authority-binding-1.0.0",
                "contract_version": "1.0.0",
                "generated_at_utc": "",
            }
        )


def build_mtg_v1_integration_package(
    *,
    payload_path: Path,
    manifest_path: Path,
    schema_contract_path: Path,
    export_contract_path: Path,
    portability_correction_path: Path,
    workspace_root: Path,
) -> tuple[Path, MTGV1AcceptanceResult]:
    """Validate A1 authority, then package it without semantic transformation."""

    acceptance = accept_mtg_v1_export(
        payload_path=payload_path,
        manifest_path=manifest_path,
        schema_contract_path=schema_contract_path,
        export_contract_path=export_contract_path,
        portability_correction_path=portability_correction_path,
    )

    if acceptance.status != "UIP_MTG_A1_EXPORT_ACCEPTANCE_PASS":
        raise MTGV1IntegrationError("A1 acceptance did not pass.")

    fields, rows = _read_payload(payload_path.resolve())

    if tuple(fields) != NATIVE_FIELDS:
        raise MTGV1IntegrationError(
            "MTG V1 field order differs from the certified 23-field interface."
        )

    if len(rows) != acceptance.payload_rows:
        raise MTGV1IntegrationError(
            "Payload row count changed after A1 acceptance."
        )

    package_id = (
        "mtg-v1-native-authority-"
        + acceptance.payload_sha256[:24]
    )

    root = workspace_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    package_path = root / package_id

    if package_path.exists():
        shutil.rmtree(package_path)

    package_path.mkdir(parents=True, exist_ok=False)

    destination = package_path / DATASET_FILENAME
    shutil.copyfile(payload_path.resolve(), destination)

    copied_sha = _sha256(destination)

    if copied_sha != acceptance.payload_sha256:
        raise MTGV1IntegrationError(
            "Bound MTG payload differs from accepted canonical bytes."
        )

    _write_manifest(
        package_path=package_path,
        row_count=len(rows),
        payload_sha256=copied_sha,
    )

    _write_platform_status(
        package_path=package_path,
        package_id=package_id,
        run_id=acceptance.source_production_authority_commit,
    )

    summary = {
        "package_id": package_id,
        "dataset_name": DATASET_NAME,
        "binding": "LOSSLESS_NATIVE_AUTHORITY",
        "source_production_authority_commit": (
            acceptance.source_production_authority_commit
        ),
        "payload_sha256": acceptance.payload_sha256,
        "payload_rows": acceptance.payload_rows,
        "field_count": acceptance.field_count,
        "native_fields_preserved": True,
        "semantic_reinterpretation_applied": False,
        "cross_asset_rank_created": False,
        "automatic_purchase_execution": False,
    }

    (package_path / "package_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return package_path, acceptance


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


def _count_nulls(
    connection: duckdb.DuckDBPyConnection,
    *,
    package_id: str,
) -> dict[str, int]:
    result: dict[str, int] = {}
    for field in NATIVE_FIELDS:
        row = connection.execute(
            f'''
            SELECT COUNT(*)
            FROM mtg_native_authority_history
            WHERE _package_id = ?
              AND "{field}" IS NULL
            ''',
            [package_id],
        ).fetchone()
        result[field] = int(row[0])
    return result


def import_mtg_v1_authority(
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
) -> MTGV1IntegrationResult:
    """Bind and transactionally import one certified MTG V1 authority."""

    package_path, acceptance = build_mtg_v1_integration_package(
        payload_path=payload_path,
        manifest_path=manifest_path,
        schema_contract_path=schema_contract_path,
        export_contract_path=export_contract_path,
        portability_correction_path=portability_correction_path,
        workspace_root=workspace_root,
    )

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

    connection = duckdb.connect(str(database_path.resolve()), read_only=True)

    try:
        package_id = import_result.package_id

        history_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                """,
                [package_id],
            ).fetchone()[0]
        )

        current_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_current
                WHERE _package_id = ?
                """,
                [package_id],
            ).fetchone()[0]
        )

        lane_counts = {
            str(lane): int(count)
            for lane, count in connection.execute(
                """
                SELECT mtg_lane, COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                GROUP BY mtg_lane
                ORDER BY mtg_lane
                """,
                [package_id],
            ).fetchall()
        }

        duplicates = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT mtg_asset_id
                    FROM mtg_native_authority_history
                    WHERE _package_id = ?
                    GROUP BY mtg_asset_id
                    HAVING COUNT(*) > 1
                )
                """,
                [package_id],
            ).fetchone()[0]
        )

        buy_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                  AND mtg_lane = 'SECRET_LAIR_V1_1'
                  AND native_purchase_status = 'BUY_CANDIDATE_NOW'
                """,
                [package_id],
            ).fetchone()[0]
        )

        buy_semantic_mismatches = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                  AND mtg_lane = 'SECRET_LAIR_V1_1'
                  AND native_purchase_status = 'BUY_CANDIDATE_NOW'
                  AND (
                      purchase_semantic IS NULL
                      OR purchase_semantic
                         <> 'MODEL_QUALIFIED_ENTRY_CANDIDATE'
                  )
                """,
                [package_id],
            ).fetchone()[0]
        )

        manual_failures = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                  AND mtg_lane = 'SECRET_LAIR_V1_1'
                  AND native_purchase_status = 'BUY_CANDIDATE_NOW'
                  AND manual_execution_price_check_required IS NOT TRUE
                """,
                [package_id],
            ).fetchone()[0]
        )

        execution_true = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                  AND execution_ready_purchase_certified IS TRUE
                """,
                [package_id],
            ).fetchone()[0]
        )

        automatic_true = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM mtg_native_authority_history
                WHERE _package_id = ?
                  AND automatic_purchase_execution IS TRUE
                """,
                [package_id],
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

        null_counts = _count_nulls(
            connection,
            package_id=package_id,
        )

    finally:
        connection.close()

    if import_result.imported_row_count != acceptance.payload_rows:
        raise MTGV1IntegrationError(
            "Transactional import row count differs from accepted payload."
        )

    if history_count != acceptance.payload_rows:
        raise MTGV1IntegrationError(
            "MTG history table row count differs from accepted payload."
        )

    if current_count != acceptance.payload_rows:
        raise MTGV1IntegrationError(
            "MTG current view row count differs from accepted payload."
        )

    if lane_counts != acceptance.lane_counts:
        raise MTGV1IntegrationError(
            "Imported lane counts differ from accepted MTG authority."
        )

    if null_counts != acceptance.blank_value_counts:
        raise MTGV1IntegrationError(
            "Imported NULL pattern differs from accepted missing-value pattern."
        )

    if duplicates != 0:
        raise MTGV1IntegrationError(
            "Duplicate governed MTG asset identifiers entered UIP."
        )

    if buy_count != acceptance.secret_lair_buy_candidate_rows:
        raise MTGV1IntegrationError(
            "Secret Lair BUY candidate count changed during integration."
        )

    if buy_semantic_mismatches != 0:
        raise MTGV1IntegrationError(
            "Secret Lair BUY semantics changed during integration."
        )

    if manual_failures != 0:
        raise MTGV1IntegrationError(
            "Secret Lair BUY manual-price-check requirement was lost."
        )

    if execution_true != 0:
        raise MTGV1IntegrationError(
            "Execution-ready purchase authority was created."
        )

    if automatic_true != 0:
        raise MTGV1IntegrationError(
            "Automatic purchase execution authority was created."
        )

    if lineage_missing != 0:
        raise MTGV1IntegrationError(
            "Imported MTG rows are missing UIP lineage."
        )

    return MTGV1IntegrationResult(
        status="UIP_MTG_A2_INTEGRATION_CERTIFICATION_PASS",
        package_id=import_result.package_id,
        import_id=import_result.import_id,
        import_status=import_result.status,
        payload_sha256=acceptance.payload_sha256,
        payload_rows=acceptance.payload_rows,
        imported_row_count=import_result.imported_row_count,
        history_row_count=history_count,
        current_row_count=current_count,
        field_count=acceptance.field_count,
        lane_counts=lane_counts,
        null_value_counts=null_counts,
        duplicate_mtg_asset_ids=duplicates,
        secret_lair_buy_candidate_rows=buy_count,
        secret_lair_buy_semantic_mismatches=buy_semantic_mismatches,
        secret_lair_buy_manual_check_failures=manual_failures,
        execution_ready_true_rows=execution_true,
        automatic_execution_true_rows=automatic_true,
        lineage_missing_rows=lineage_missing,
        native_fields_preserved=True,
        cross_asset_rank_created=False,
        generic_recommendation_created=False,
        generic_forecast_created=False,
        generic_risk_created=False,
        uip_integration_certified=True,
    )


def result_to_dict(
    result: MTGV1IntegrationResult,
) -> dict[str, object]:
    """Return a stable JSON-serializable certification result."""

    return asdict(result)