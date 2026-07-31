"""Certified MTG delivery intake through the canonical UIP import engine."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.loader import ImportResult, import_package


MTG_JSON_MANIFEST = "export_manifest.json"
UIP_CSV_MANIFEST = "export_manifest.csv"
PLATFORM_STATUS = "platform_status.csv"
PACKAGE_SUMMARY = "package_summary.json"

SUPPORTED_DELIVERY_CONTRACTS = {
    "uip-mtg-delivery-v1",
}


HISTORICAL_PERFORMANCE_FILENAME = (
    "historical_performance.csv"
)

UNIVERSAL_HISTORICAL_COLUMNS = (
    "contract_version",
    "platform_id",
    "run_id",
    "universal_asset_id",
    "performance_status",
    "performance_eligible",
    "historical_start_date",
    "historical_end_date",
    "historical_start_value",
    "historical_end_value",
    "elapsed_days",
    "observation_count",
    "distinct_date_count",
    "source_count",
    "historical_sources",
    "total_return_pct",
    "cagr_pct",
    "annualized_return_pct",
    "minimum_value",
    "maximum_value",
    "data_quality",
    "suppression_reason",
    "currency",
    "source_system",
    "model_version",
    "generated_at_utc",
    "notes",
    "metadata_json",
)

MTG_NATIVE_HISTORICAL_COLUMNS = (
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
)


class MTGPackageIntakeError(RuntimeError):
    """Raised when an MTG delivery cannot enter the UIP import boundary."""


@dataclass(frozen=True)
class NormalizedDataset:
    """One dataset materialized into the canonical UIP package workspace."""

    dataset_name: str
    filename: str
    row_count: int
    sha256: str
    size_bytes: int
    required: bool
    validation_status: str


@dataclass(frozen=True)
class MTGPackageIntakeResult:
    """Immutable result of one certified MTG package intake."""

    package_id: str
    source_package_path: str
    normalized_package_path: str
    database_path: str
    delivery_contract: str
    manifest_sha256: str
    imported_row_count: int
    imported_datasets: tuple[str, ...]
    import_id: str
    import_status: str
    intake_status: str
    completed_at_utc: str
    result_path: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest().lower()


def _count_csv_rows(path: Path) -> int:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.reader(handle)

        try:
            next(reader)
        except StopIteration:
            return 0

        return sum(
            1
            for row in reader
            if any(str(value).strip() for value in row)
        )


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8-sig")
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise MTGPackageIntakeError(
            f"Unable to parse JSON file: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise MTGPackageIntakeError(
            f"JSON file must contain an object: {path}"
        )

    return payload


def _read_first_csv_row(
    path: Path,
) -> dict[str, str]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            raise MTGPackageIntakeError(
                f"CSV has no header: {path}"
            )

        try:
            row = next(reader)
        except StopIteration as exc:
            raise MTGPackageIntakeError(
                f"CSV contains no data rows: {path}"
            ) from exc

    return {
        str(key).strip(): (
            ""
            if value is None
            else str(value).strip()
        )
        for key, value in row.items()
        if key is not None
    }


def _read_csv_dicts(
    path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            raise MTGPackageIntakeError(
                f"CSV has no header: {path}"
            )

        fieldnames = [
            str(value).strip()
            for value in reader.fieldnames
        ]

        rows = [
            {
                str(key).strip(): (
                    ""
                    if value is None
                    else str(value).strip()
                )
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]

    return fieldnames, rows


def _first_nonblank(
    row: dict[str, str],
    candidates: tuple[str, ...],
    *,
    default: str = "",
) -> str:
    normalized = {
        str(key).strip().lower(): str(value).strip()
        for key, value in row.items()
        if key is not None and value is not None
    }

    for candidate in candidates:
        value = normalized.get(
            candidate.strip().lower(),
            "",
        )

        if value:
            return value

    return default


def _required_alias_value(
    row: dict[str, str],
    candidates: tuple[str, ...],
    *,
    label: str,
) -> str:
    value = _first_nonblank(
        row,
        candidates,
    )

    if not value:
        raise MTGPackageIntakeError(
            "MTG platform status has no usable "
            f"{label}. Accepted columns: "
            f"{list(candidates)}"
        )

    return value


def _required_value(
    row: dict[str, str],
    field: str,
    *,
    row_number: int,
) -> str:
    value = str(row.get(field, "")).strip()

    if not value:
        raise MTGPackageIntakeError(
            "MTG historical-performance row "
            f"{row_number} has blank required field: "
            f"{field}"
        )

    return value


def _normalize_historical_performance(
    *,
    source_file: Path,
    destination_file: Path,
    platform_status: dict[str, str],
    delivery_manifest: dict[str, Any],
) -> NormalizedDataset:
    source_fields, source_rows = (
        _read_csv_dicts(source_file)
    )

    if tuple(source_fields) == UNIVERSAL_HISTORICAL_COLUMNS:
        shutil.copy2(
            source_file,
            destination_file,
        )

        return NormalizedDataset(
            dataset_name="historical_performance",
            filename=destination_file.name,
            row_count=len(source_rows),
            sha256=_sha256(destination_file),
            size_bytes=destination_file.stat().st_size,
            required=True,
            validation_status="PASS",
        )

    missing_native = [
        field
        for field in MTG_NATIVE_HISTORICAL_COLUMNS
        if field not in source_fields
    ]

    if missing_native:
        raise MTGPackageIntakeError(
            "MTG historical-performance schema is "
            "neither native nor universal. Missing "
            f"native fields: {missing_native}"
        )

    platform_id = _required_alias_value(
        platform_status,
        (
            "platform_id",
            "platform",
            "source_platform",
        ),
        label="platform identifier",
    )

    run_id = _first_nonblank(
        platform_status,
        (
            "run_id",
            "platform_run_id",
            "source_run_id",
        ),
    )

    if not run_id:
        run_id = str(
            delivery_manifest.get(
                "package_id",
                "",
            )
        ).strip()

    if not run_id:
        raise MTGPackageIntakeError(
            "Unable to establish historical-performance "
            "run_id from platform status or package_id."
        )

    contract_version = _first_nonblank(
        platform_status,
        (
            "contract_version",
            "universal_contract_version",
            "schema_version",
        ),
        default="1.0.0",
    )

    model_version = _first_nonblank(
        platform_status,
        (
            "adapter_version",
            "model_version",
            "platform_version",
            "interface_name",
            "version",
        ),
    )

    generated_at_utc = _required_alias_value(
        platform_status,
        (
            "generated_at_utc",
            "run_completed_at_utc",
            "last_updated_at_utc",
            "generated_at",
            "completed_at_utc",
        ),
        label="generation timestamp",
    )

    universal_rows: list[dict[str, str]] = []

    for row_number, row in enumerate(
        source_rows,
        start=2,
    ):
        universal_asset_id = _required_value(
            row,
            "universal_mtg_product_id",
            row_number=row_number,
        )

        metadata = {
            "investment_product_id": row.get(
                "investment_product_id",
                "",
            ),
            "canonical_product_name": row.get(
                "canonical_product_name",
                "",
            ),
            "asset_class": row.get(
                "asset_class",
                "",
            ),
            "forecast_eligible": row.get(
                "forecast_eligible",
                "",
            ),
            "recommendation_eligible": row.get(
                "recommendation_eligible",
                "",
            ),
            "one_year_base_usd": row.get(
                "one_year_base_usd",
                "",
            ),
            "three_year_base_usd": row.get(
                "three_year_base_usd",
                "",
            ),
            "five_year_base_usd": row.get(
                "five_year_base_usd",
                "",
            ),
        }

        universal_rows.append(
            {
                "contract_version": contract_version,
                "platform_id": platform_id,
                "run_id": run_id,
                "universal_asset_id": (
                    universal_asset_id
                ),
                "performance_status": _required_value(
                    row,
                    "historical_performance_status",
                    row_number=row_number,
                ),
                "performance_eligible": (
                    _required_value(
                        row,
                        "historical_performance_eligible",
                        row_number=row_number,
                    )
                ),
                "historical_start_date": row.get(
                    "historical_start_date",
                    "",
                ),
                "historical_end_date": row.get(
                    "historical_end_date",
                    "",
                ),
                "historical_start_value": row.get(
                    "historical_start_value_usd",
                    "",
                ),
                "historical_end_value": row.get(
                    "historical_end_value_usd",
                    "",
                ),
                "elapsed_days": row.get(
                    "historical_elapsed_days",
                    "",
                ),
                "observation_count": row.get(
                    "historical_observation_count",
                    "",
                ),
                "distinct_date_count": row.get(
                    "historical_distinct_dates",
                    "",
                ),
                "source_count": row.get(
                    "historical_source_count",
                    "",
                ),
                "historical_sources": row.get(
                    "historical_sources",
                    "",
                ),
                "total_return_pct": row.get(
                    "historical_total_return_pct",
                    "",
                ),
                "cagr_pct": row.get(
                    "historical_cagr_pct",
                    "",
                ),
                "annualized_return_pct": row.get(
                    "historical_annualized_return_pct",
                    "",
                ),
                "minimum_value": row.get(
                    "historical_min_value_usd",
                    "",
                ),
                "maximum_value": row.get(
                    "historical_max_value_usd",
                    "",
                ),
                "data_quality": _required_value(
                    row,
                    "historical_data_quality",
                    row_number=row_number,
                ),
                "suppression_reason": row.get(
                    "historical_suppression_reason",
                    "",
                ),
                "currency": (
                    str(
                        row.get("currency", "")
                    ).strip()
                    or "USD"
                ),
                "source_system": (
                    "mtg-investment-terminal"
                ),
                "model_version": model_version,
                "generated_at_utc": generated_at_utc,
                "notes": (
                    "Normalized from "
                    "uip-mtg-delivery-v1 native "
                    "historical schema."
                ),
                "metadata_json": json.dumps(
                    metadata,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        )

    with destination_file.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                UNIVERSAL_HISTORICAL_COLUMNS
            ),
        )
        writer.writeheader()
        writer.writerows(universal_rows)

    return NormalizedDataset(
        dataset_name="historical_performance",
        filename=destination_file.name,
        row_count=len(universal_rows),
        sha256=_sha256(destination_file),
        size_bytes=destination_file.stat().st_size,
        required=True,
        validation_status="PASS",
    )


def _validate_source_package(
    source_package: Path,
) -> dict[str, Any]:
    source = source_package.resolve()

    if not source.exists():
        raise MTGPackageIntakeError(
            f"MTG package does not exist: {source}"
        )

    if not source.is_dir():
        raise MTGPackageIntakeError(
            f"MTG package is not a directory: {source}"
        )

    manifest_path = source / MTG_JSON_MANIFEST
    status_path = source / PLATFORM_STATUS

    if not manifest_path.is_file():
        raise MTGPackageIntakeError(
            f"MTG JSON manifest is missing: {manifest_path}"
        )

    if not status_path.is_file():
        raise MTGPackageIntakeError(
            f"Platform status is missing: {status_path}"
        )

    manifest = _load_json_object(manifest_path)

    if str(manifest.get("status", "")).upper() != "PASS":
        raise MTGPackageIntakeError(
            "MTG delivery manifest is not certified PASS."
        )

    delivery_contract = str(
        manifest.get("delivery_contract", "")
    ).strip()

    if delivery_contract not in SUPPORTED_DELIVERY_CONTRACTS:
        raise MTGPackageIntakeError(
            "Unsupported MTG delivery contract: "
            f"{delivery_contract or '<blank>'}"
        )

    package_id = str(
        manifest.get("package_id", "")
    ).strip()

    if not package_id:
        raise MTGPackageIntakeError(
            "MTG delivery manifest has no package_id."
        )

    files = manifest.get("files")

    if not isinstance(files, dict) or not files:
        raise MTGPackageIntakeError(
            "MTG delivery manifest contains no files."
        )

    return manifest


def _dataset_name(filename: str) -> str:
    return Path(filename).stem.lower()


def _validate_manifest_file(
    source_package: Path,
    filename: str,
    declaration: Any,
) -> NormalizedDataset:
    if not isinstance(declaration, dict):
        raise MTGPackageIntakeError(
            f"Invalid file declaration for {filename}."
        )

    relative = Path(filename)

    if relative.is_absolute() or ".." in relative.parts:
        raise MTGPackageIntakeError(
            f"Unsafe MTG package filename: {filename}"
        )

    source_file = (
        source_package.resolve()
        / relative
    ).resolve()

    try:
        source_file.relative_to(
            source_package.resolve()
        )
    except ValueError as exc:
        raise MTGPackageIntakeError(
            f"MTG package filename escapes package root: {filename}"
        ) from exc

    if not source_file.is_file():
        raise MTGPackageIntakeError(
            f"Declared MTG package file is missing: {filename}"
        )

    expected_sha256 = str(
        declaration.get("sha256", "")
    ).strip().lower()

    expected_size = declaration.get("size_bytes")

    actual_sha256 = _sha256(source_file)
    actual_size = source_file.stat().st_size

    if not expected_sha256:
        raise MTGPackageIntakeError(
            f"No SHA-256 declared for {filename}."
        )

    if actual_sha256 != expected_sha256:
        raise MTGPackageIntakeError(
            f"SHA-256 mismatch for {filename}."
        )

    if expected_size is not None:
        try:
            declared_size = int(expected_size)
        except (TypeError, ValueError) as exc:
            raise MTGPackageIntakeError(
                f"Invalid size declaration for {filename}."
            ) from exc

        if actual_size != declared_size:
            raise MTGPackageIntakeError(
                f"File-size mismatch for {filename}."
            )

    row_count = (
        _count_csv_rows(source_file)
        if source_file.suffix.lower() == ".csv"
        else 0
    )

    return NormalizedDataset(
        dataset_name=_dataset_name(filename),
        filename=filename,
        row_count=row_count,
        sha256=actual_sha256,
        size_bytes=actual_size,
        required=True,
        validation_status="PASS",
    )


def _write_canonical_manifest(
    workspace: Path,
    datasets: tuple[NormalizedDataset, ...],
) -> Path:
    manifest_path = workspace / UIP_CSV_MANIFEST

    fieldnames = [
        "dataset_name",
        "filename",
        "row_count",
        "sha256",
        "required",
        "validation_status",
    ]

    with manifest_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for dataset in datasets:
            writer.writerow(
                {
                    "dataset_name": dataset.dataset_name,
                    "filename": dataset.filename,
                    "row_count": dataset.row_count,
                    "sha256": dataset.sha256,
                    "required": str(
                        dataset.required
                    ).lower(),
                    "validation_status": (
                        dataset.validation_status
                    ),
                }
            )

    return manifest_path


def normalize_mtg_delivery(
    source_package: Path,
    workspace_root: Path,
) -> tuple[
    Path,
    dict[str, Any],
    tuple[NormalizedDataset, ...],
]:
    """Create an isolated canonical UIP package from a certified MTG delivery."""

    source = source_package.resolve()
    workspace_root = workspace_root.resolve()

    manifest = _validate_source_package(source)
    package_id = str(manifest["package_id"])

    workspace = workspace_root / package_id

    if workspace.exists():
        shutil.rmtree(workspace)

    workspace.mkdir(
        parents=True,
        exist_ok=False,
    )

    files = manifest["files"]
    datasets: list[NormalizedDataset] = []

    try:
        platform_status = _read_first_csv_row(
            source / PLATFORM_STATUS
        )

        for filename in sorted(files):
            source_dataset = _validate_manifest_file(
                source,
                filename,
                files[filename],
            )

            source_file = source / filename
            destination_file = workspace / filename

            if (
                filename
                == HISTORICAL_PERFORMANCE_FILENAME
            ):
                dataset = (
                    _normalize_historical_performance(
                        source_file=source_file,
                        destination_file=destination_file,
                        platform_status=platform_status,
                        delivery_manifest=manifest,
                    )
                )
            else:
                shutil.copy2(
                    source_file,
                    destination_file,
                )

                dataset = source_dataset

            datasets.append(dataset)

        summary_source = source / PACKAGE_SUMMARY

        if summary_source.is_file():
            shutil.copy2(
                summary_source,
                workspace / PACKAGE_SUMMARY,
            )
        else:
            (
                workspace / PACKAGE_SUMMARY
            ).write_text(
                json.dumps(
                    manifest,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

        shutil.copy2(
            source / MTG_JSON_MANIFEST,
            workspace / MTG_JSON_MANIFEST,
        )

        _write_canonical_manifest(
            workspace,
            tuple(datasets),
        )
    except Exception:
        shutil.rmtree(
            workspace,
            ignore_errors=True,
        )
        raise

    return (
        workspace,
        manifest,
        tuple(datasets),
    )


def _build_config(
    repository_root: Path,
    database_path: Path,
    validation_root: Path,
) -> ImportEngineConfig:
    repository = repository_root.resolve()

    return ImportEngineConfig(
        repository_root=repository,
        database_path=database_path.resolve(),
        schema_root=(
            repository
            / "schemas"
            / "v1"
            / "csv"
        ),
        integration_root=(
            repository
            / "data"
            / "integration"
        ),
        validation_root=validation_root.resolve(),
    )


def _write_intake_result(
    result_root: Path,
    result: dict[str, Any],
) -> Path:
    result_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    package_id = str(result["package_id"])
    result_path = (
        result_root
        / f"{package_id}-intake-result.json"
    )

    if result_path.exists():
        existing = _load_json_object(result_path)

        if existing != result:
            raise MTGPackageIntakeError(
                "Immutable intake result already exists with "
                f"different content: {result_path}"
            )

        return result_path

    result_path.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return result_path


def intake_certified_mtg_package(
    *,
    repository_root: Path,
    source_package: Path,
    database_path: Path,
    workspace_root: Path,
    validation_root: Path,
    result_root: Path,
    force: bool = False,
) -> MTGPackageIntakeResult:
    """Normalize and transactionally import one certified MTG delivery."""

    workspace, manifest, _ = normalize_mtg_delivery(
        source_package=source_package,
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
        package_path=workspace,
        force=force,
    )

    manifest_sha256 = _sha256(
        workspace / UIP_CSV_MANIFEST
    )

    completed_at_utc = _utc_now()

    result_payload = {
        "package_id": import_result.package_id,
        "source_package_path": str(
            source_package.resolve()
        ),
        "normalized_package_path": str(workspace),
        "database_path": str(
            database_path.resolve()
        ),
        "delivery_contract": str(
            manifest["delivery_contract"]
        ),
        "manifest_sha256": manifest_sha256,
        "imported_row_count": (
            import_result.imported_row_count
        ),
        "imported_datasets": sorted(
            dataset.dataset_name
            for dataset
            in import_result.dataset_results
        ),
        "import_id": import_result.import_id,
        "import_status": import_result.status,
        "intake_status": "PASS",
        "completed_at_utc": completed_at_utc,
    }

    provisional_path = (
        result_root.resolve()
        / (
            f"{import_result.package_id}"
            "-intake-result.json"
        )
    )

    result_payload["result_path"] = str(
        provisional_path
    )

    result_path = _write_intake_result(
        result_root.resolve(),
        result_payload,
    )

    return MTGPackageIntakeResult(
        package_id=import_result.package_id,
        source_package_path=result_payload[
            "source_package_path"
        ],
        normalized_package_path=result_payload[
            "normalized_package_path"
        ],
        database_path=result_payload[
            "database_path"
        ],
        delivery_contract=result_payload[
            "delivery_contract"
        ],
        manifest_sha256=manifest_sha256,
        imported_row_count=(
            import_result.imported_row_count
        ),
        imported_datasets=tuple(
            result_payload["imported_datasets"]
        ),
        import_id=import_result.import_id,
        import_status=import_result.status,
        intake_status="PASS",
        completed_at_utc=completed_at_utc,
        result_path=str(result_path),
    )


def result_to_dict(
    result: MTGPackageIntakeResult,
) -> dict[str, Any]:
    """Serialize an intake result without exposing implementation details."""

    return asdict(result)
