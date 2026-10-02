"""Transactional loading of Universal Integration Packages into DuckDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import csv
import json
import uuid

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.exceptions import (
    DuplicatePackageError,
    ImportTransactionError,
)
from foundation.import_engine.integrity import (
    PackageValidationResult,
    validate_package_integrity,
)
from foundation.import_engine.package import (
    UniversalPackage,
    discover_package,
)


SUPPORTED_DATASETS = {
    "asset_master": "asset_master_history",
    "forecasts": "forecasts_history",
    "recommendations": "recommendations_history",
    "risk_metrics": "risk_metrics_history",
    "portfolio_positions": "portfolio_positions_history",
    "platform_status": "platform_status_history",
    "macro_signals": "macro_signals_history",
    "historical_performance": "historical_performance_history",
    "mtg_native_authority": "mtg_native_authority_history",
}

LINEAGE_COLUMNS = (
    "_import_id",
    "_package_id",
    "_source_platform",
    "_source_filename",
    "_source_row_number",
    "_manifest_sha256",
    "_imported_at_utc",
)


CONTRACT_TO_HISTORY_ALIASES = {
    "asset_master": {
        "is_active": "active",
        "data_source": "source_system",
        "first_available_date": "first_observed_date",
    },
    "forecasts": {
        "forecast_value_base": "point_forecast",
        "forecast_value_bear": "lower_bound",
        "forecast_value_bull": "upper_bound",
        "expected_total_return": "expected_return",
        "probability_positive_return": "probability_positive",
        "forecast_confidence": "confidence_score",
        "scenario_name": "scenario",
    },
    "recommendations": {
        "rationale_summary": "rationale",
        "rationale": "rationale",
        "primary_risk": "risk_summary",
        "confidence": "confidence_score",
        "recommendation_score": "normalized_score",
    },
    "platform_status": {
        "status": "run_status",
        "message": "status_message",
        "last_successful_run_at_utc": "run_completed_at_utc",
    },
    "risk_metrics": {
        "annualized_volatility": "volatility",
        "downside_deviation": "downside_volatility",
        "value_at_risk_95": "value_at_risk",
        "risk_notes": "notes",
    },
}


def _parse_metadata_json(value: str) -> dict[str, object]:
    raw = str(value or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"source_metadata_raw": raw}

    if isinstance(parsed, dict):
        return dict(parsed)

    return {"source_metadata_value": parsed}


def _translate_contract_row(
    dataset_name: str,
    row: dict[str, str],
    business_columns: list[str],
) -> dict[str, object]:
    """Translate a governed package row into the history-table shape losslessly."""

    aliases = CONTRACT_TO_HISTORY_ALIASES.get(dataset_name, {})
    business = set(business_columns)

    translated: dict[str, object] = {}
    consumed_source_fields: set[str] = set()

    # Same-name fields are authoritative when the destination supports them.
    for column in business_columns:
        if column == "metadata_json":
            continue
        if column in row:
            translated[column] = _coerce_blank(row.get(column, ""))
            consumed_source_fields.add(column)

    # Explicit contract -> history aliases fill only destination fields that
    # were not already populated by an exact-name source field.
    for source_column, destination_column in aliases.items():
        if source_column not in row:
            continue
        if destination_column not in business:
            continue

        existing = translated.get(destination_column)
        if existing is None:
            translated[destination_column] = _coerce_blank(
                row.get(source_column, "")
            )

        consumed_source_fields.add(source_column)

    # Preserve every source field that has no dedicated history column.
    metadata = _parse_metadata_json(row.get("metadata_json", ""))

    unmapped = {}
    for key, value in row.items():
        if key == "metadata_json":
            continue
        if key in consumed_source_fields:
            continue
        if key in business:
            continue
        if key in aliases:
            continue

        normalized = _coerce_blank(value)
        if normalized is not None:
            unmapped[key] = normalized

    if unmapped:
        existing_unmapped = metadata.get("unmapped_contract_fields")
        if isinstance(existing_unmapped, dict):
            merged_unmapped = dict(existing_unmapped)
            merged_unmapped.update(unmapped)
            metadata["unmapped_contract_fields"] = merged_unmapped
        else:
            metadata["unmapped_contract_fields"] = unmapped

    if "metadata_json" in business:
        translated["metadata_json"] = (
            json.dumps(metadata, sort_keys=True, separators=(",", ":"))
            if metadata
            else None
        )

    return translated


@dataclass(frozen=True)
class DatasetLoadResult:
    """Result for one imported Universal dataset."""

    dataset_name: str
    source_filename: str
    imported_row_count: int


@dataclass(frozen=True)
class ImportResult:
    """Result of one transactional package import."""

    import_id: str
    package_id: str
    platform_id: str
    imported_row_count: int
    dataset_results: tuple[DatasetLoadResult, ...]
    status: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _safe_identifier(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
    if not value or any(char not in allowed for char in value):
        raise ImportTransactionError(f"Unsafe SQL identifier: {value}")
    return value


def _table_columns(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
) -> list[str]:
    table_name = _safe_identifier(table_name)
    rows = connection.execute(
        f"PRAGMA table_info('{table_name}')"
    ).fetchall()
    return [str(row[1]) for row in rows]


def _read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ImportTransactionError(f"CSV has no header: {path}")

        fieldnames = [str(name).strip() for name in reader.fieldnames]
        rows = []
        for row in reader:
            normalized = {
                str(key).strip(): "" if value is None else str(value).strip()
                for key, value in row.items()
                if key is not None
            }
            if any(value != "" for value in normalized.values()):
                rows.append(normalized)

        return fieldnames, rows


def _coerce_blank(value: str):
    return None if value == "" else value


def _dataset_name_from_filename(filename: str) -> str:
    return Path(filename).stem.lower()


def _find_manifest_entry(package: UniversalPackage, dataset_name: str):
    for entry in package.manifest_entries:
        entry_name = (entry.dataset_name or "").strip().lower()
        file_name = _dataset_name_from_filename(entry.filename)
        if entry_name == dataset_name or file_name == dataset_name:
            return entry
    return None


def _duplicate_exists(
    connection: duckdb.DuckDBPyConnection,
    package_id: str,
    manifest_sha256: str,
) -> bool:
    result = connection.execute(
        """
        SELECT COUNT(*)
        FROM universal_imports
        WHERE import_status = 'IMPORTED'
          AND (package_id = ? OR manifest_sha256 = ?)
        """,
        [package_id, manifest_sha256],
    ).fetchone()
    return int(result[0]) > 0


def _insert_rows(
    connection: duckdb.DuckDBPyConnection,
    dataset_name: str,
    table_name: str,
    csv_path: Path,
    import_id: str,
    package: UniversalPackage,
    manifest_sha256: str,
    imported_at_utc: datetime,
) -> int:
    table_name = _safe_identifier(table_name)
    table_columns = _table_columns(connection, table_name)
    business_columns = [c for c in table_columns if c not in LINEAGE_COLUMNS]

    _, rows = _read_csv_rows(csv_path)
    if not rows:
        return 0

    unknown_required = [
        col for col in business_columns
        if col not in rows[0] and col.startswith("_")
    ]
    if unknown_required:
        raise ImportTransactionError(
            f"Unexpected required columns for {table_name}: {unknown_required}"
        )

    insert_columns = business_columns + list(LINEAGE_COLUMNS)
    placeholders = ", ".join(["?"] * len(insert_columns))
    quoted_columns = ", ".join(f'"{col}"' for col in insert_columns)

    sql = (
        f'INSERT INTO "{table_name}" ({quoted_columns}) '
        f"VALUES ({placeholders})"
    )

    payload = []
    for row_number, row in enumerate(rows, start=2):
        translated = _translate_contract_row(
            dataset_name,
            row,
            business_columns,
        )
        values = [
            translated.get(col)
            for col in business_columns
        ]
        values.extend(
            [
                import_id,
                package.identity.package_id,
                package.identity.platform_id,
                str(csv_path.relative_to(package.package_path)),
                row_number,
                manifest_sha256,
                imported_at_utc,
            ]
        )
        payload.append(values)

    connection.executemany(sql, payload)
    return len(payload)


def import_package(
    config: ImportEngineConfig,
    package_path: Path,
    *,
    force: bool = False,
) -> ImportResult:
    """Validate and transactionally import one Universal Integration Package."""

    package = discover_package(package_path)
    validation = validate_package_integrity(package)

    if not validation.passed:
        raise ImportTransactionError(
            f"Package integrity validation failed with "
            f"{validation.error_count} error(s)."
        )

    import_id = str(uuid.uuid4())
    imported_at_utc = _utc_now()

    connection = duckdb.connect(str(config.database_path))

    try:
        if _duplicate_exists(
            connection,
            package.identity.package_id,
            validation.manifest_sha256,
        ) and not force:
            raise DuplicatePackageError(
                f"Package already imported: {package.identity.package_id}"
            )

        dataset_results: list[DatasetLoadResult] = []
        total_rows = 0

        connection.execute("BEGIN TRANSACTION")

        connection.execute(
            """
            INSERT INTO universal_imports (
                import_id,
                package_id,
                platform_id,
                run_id,
                adapter_version,
                contract_version,
                import_mode,
                import_status,
                package_path,
                manifest_sha256,
                discovered_at_utc,
                started_at_utc,
                dataset_count,
                expected_row_count,
                imported_row_count,
                warning_count,
                error_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'IMPORTING', ?, ?, ?, ?, 0, 0, 0, ?, 0)
            """,
            [
                import_id,
                package.identity.package_id,
                package.identity.platform_id,
                package.identity.run_id,
                package.identity.adapter_version,
                package.identity.contract_version,
                "FORCE" if force else "STANDARD",
                str(package.package_path),
                validation.manifest_sha256,
                imported_at_utc,
                imported_at_utc,
                validation.warning_count,
            ],
        )

        for dataset_name, table_name in SUPPORTED_DATASETS.items():
            entry = _find_manifest_entry(package, dataset_name)
            if entry is None:
                continue

            source_path = package.package_path / entry.filename
            row_count = _insert_rows(
                connection=connection,
                dataset_name=dataset_name,
                table_name=table_name,
                csv_path=source_path,
                import_id=import_id,
                package=package,
                manifest_sha256=validation.manifest_sha256,
                imported_at_utc=imported_at_utc,
            )

            import_dataset_id = str(uuid.uuid4())

            connection.execute(
                """
                INSERT INTO universal_import_datasets (
                    import_dataset_id,
                    import_id,
                    dataset_name,
                    source_filename,
                    required,
                    expected_row_count,
                    imported_row_count,
                    source_sha256,
                    calculated_sha256,
                    contract_status,
                    checksum_status,
                    load_status,
                    warning_count,
                    error_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'IMPORTED', 0, 0)
                """,
                [
                    import_dataset_id,
                    import_id,
                    dataset_name,
                    entry.filename,
                    entry.required,
                    entry.expected_row_count or row_count,
                    row_count,
                    entry.expected_sha256,
                    entry.expected_sha256,
                    entry.validation_status or "PASS",
                    "PASS",
                ],
            )

            dataset_results.append(
                DatasetLoadResult(
                    dataset_name=dataset_name,
                    source_filename=entry.filename,
                    imported_row_count=row_count,
                )
            )
            total_rows += row_count

        connection.execute(
            """
            INSERT INTO universal_packages (
                package_id,
                platform_id,
                run_id,
                adapter_version,
                contract_version,
                package_status,
                package_path,
                manifest_sha256,
                generated_at_utc,
                first_seen_at_utc,
                last_seen_at_utc,
                successful_import_id
            )
            VALUES (?, ?, ?, ?, ?, 'IMPORTED', ?, ?, ?, ?, ?, ?)
            ON CONFLICT(package_id) DO UPDATE SET
                package_status = excluded.package_status,
                package_path = excluded.package_path,
                manifest_sha256 = excluded.manifest_sha256,
                last_seen_at_utc = excluded.last_seen_at_utc,
                successful_import_id = excluded.successful_import_id
            """,
            [
                package.identity.package_id,
                package.identity.platform_id,
                package.identity.run_id,
                package.identity.adapter_version,
                package.identity.contract_version,
                str(package.package_path),
                validation.manifest_sha256,
                package.identity.generated_at_utc or None,
                imported_at_utc,
                imported_at_utc,
                import_id,
            ],
        )

        connection.execute(
            """
            UPDATE universal_imports
            SET import_status = 'IMPORTED',
                completed_at_utc = ?,
                dataset_count = ?,
                imported_row_count = ?,
                expected_row_count = ?
            WHERE import_id = ?
            """,
            [
                _utc_now(),
                len(dataset_results),
                total_rows,
                total_rows,
                import_id,
            ],
        )

        connection.execute("COMMIT")

        return ImportResult(
            import_id=import_id,
            package_id=package.identity.package_id,
            platform_id=package.identity.platform_id,
            imported_row_count=total_rows,
            dataset_results=tuple(dataset_results),
            status="IMPORTED",
        )

    except Exception as exc:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass

        if isinstance(exc, DuplicatePackageError):
            raise

        raise ImportTransactionError(str(exc)) from exc
    finally:
        connection.close()
