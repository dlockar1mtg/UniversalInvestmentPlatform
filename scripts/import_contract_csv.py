from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from validate_contracts import infer_contract_name, validate_csv


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "integration" / "uiip_integration.duckdb"

SUPPORTED_CONTRACTS = {
    "platform_status",
    "asset_master",
    "recommendations",
    "forecasts",
    "risk_metrics",
    "portfolio_positions",
    "macro_signals",
    "export_manifest",
}

DATE_COLUMNS = {
    "platform_status": ["data_as_of_date"],
    "asset_master": ["first_available_date"],
    "recommendations": ["as_of_date"],
    "forecasts": ["forecast_origin_date", "forecast_date"],
    "risk_metrics": ["as_of_date"],
    "portfolio_positions": ["as_of_date"],
    "macro_signals": ["as_of_date"],
    "export_manifest": [],
}

TIMESTAMP_COLUMNS = {
    "platform_status": [
        "run_started_at_utc",
        "run_completed_at_utc",
    ],
    "asset_master": ["last_updated_at_utc"],
    "recommendations": ["generated_at_utc"],
    "forecasts": ["generated_at_utc"],
    "risk_metrics": ["generated_at_utc"],
    "portfolio_positions": ["last_updated_at_utc"],
    "macro_signals": ["generated_at_utc"],
    "export_manifest": ["created_at_utc"],
}

BOOLEAN_COLUMNS = {
    "asset_master": ["is_active", "investable"],
}

INTEGER_COLUMNS = {
    "platform_status": [
        "records_published",
        "warning_count",
        "error_count",
    ],
    "forecasts": ["forecast_horizon_months"],
    "risk_metrics": ["lookback_days"],
    "export_manifest": [
        "record_count",
        "file_size_bytes",
    ],
}

FLOAT_COLUMNS = {
    "recommendations": [
        "normalized_score",
        "confidence_score",
        "platform_native_score",
        "target_weight",
        "minimum_weight",
        "maximum_weight",
    ],
    "forecasts": [
        "current_value",
        "forecast_value_base",
        "forecast_value_bear",
        "forecast_value_bull",
        "expected_total_return",
        "expected_cagr",
        "probability_positive_return",
        "forecast_confidence",
    ],
    "risk_metrics": [
        "risk_score",
        "annualized_volatility",
        "maximum_drawdown",
        "downside_deviation",
        "value_at_risk_95",
        "liquidity_risk_score",
        "concentration_risk_score",
        "model_risk_score",
        "data_quality_score",
    ],
    "portfolio_positions": [
        "quantity",
        "unit_value",
        "position_value",
        "cost_basis",
        "unrealized_gain_loss",
        "current_weight",
        "target_weight",
        "minimum_weight",
        "maximum_weight",
        "monthly_allocation_amount",
    ],
    "macro_signals": [
        "signal_value",
        "normalized_score",
        "confidence_score",
    ],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_boolean(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.lower()

    return normalized.map(
        {
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False,
        }
    )


def prepare_frame(path: Path, contract_name: str) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str).replace({"": None})

    for column in DATE_COLUMNS.get(contract_name, []):
        if column in frame.columns:
            frame[column] = pd.to_datetime(
                frame[column],
                errors="coerce",
            ).dt.date

    for column in TIMESTAMP_COLUMNS.get(contract_name, []):
        if column in frame.columns:
            frame[column] = pd.to_datetime(
                frame[column],
                errors="coerce",
                utc=True,
            ).dt.tz_localize(None)

    for column in BOOLEAN_COLUMNS.get(contract_name, []):
        if column in frame.columns:
            frame[column] = normalize_boolean(frame[column])

    for column in INTEGER_COLUMNS.get(contract_name, []):
        if column in frame.columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            ).astype("Int64")

    for column in FLOAT_COLUMNS.get(contract_name, []):
        if column in frame.columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

    frame.insert(0, "import_batch_id", str(uuid.uuid4()))
    frame["imported_at_utc"] = utc_now()

    return frame


def already_imported(
    connection: duckdb.DuckDBPyConnection,
    file_hash: str,
    contract_name: str,
) -> bool:
    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM meta.import_runs
        WHERE source_file_sha256 = ?
          AND contract_name = ?
          AND import_status = 'success'
        """,
        [file_hash, contract_name],
    ).fetchone()[0]

    return count > 0


def identify_platform(frame: pd.DataFrame) -> tuple[str | None, str | None]:
    platform_id = None
    run_id = None

    if "platform_id" in frame.columns and not frame.empty:
        platform_id = str(frame.iloc[0]["platform_id"])

    if "run_id" in frame.columns and not frame.empty:
        run_id = str(frame.iloc[0]["run_id"])

    return platform_id, run_id


def write_import_run(
    connection: duckdb.DuckDBPyConnection,
    values: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO meta.import_runs (
            import_batch_id,
            contract_name,
            contract_version,
            platform_id,
            platform_run_id,
            source_file,
            source_file_sha256,
            source_record_count,
            imported_record_count,
            rejected_record_count,
            validation_status,
            import_status,
            started_at_utc,
            completed_at_utc,
            message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            values["import_batch_id"],
            values["contract_name"],
            values.get("contract_version"),
            values.get("platform_id"),
            values.get("platform_run_id"),
            values["source_file"],
            values["source_file_sha256"],
            values["source_record_count"],
            values["imported_record_count"],
            values["rejected_record_count"],
            values["validation_status"],
            values["import_status"],
            values["started_at_utc"],
            values.get("completed_at_utc"),
            values.get("message"),
        ],
    )


def import_contract(path: Path, contract_name: str) -> int:
    if contract_name not in SUPPORTED_CONTRACTS:
        print(
            f"Unsupported contract: {contract_name}",
            file=sys.stderr,
        )
        return 2

    validation_report = validate_csv(path, contract_name)

    if not validation_report["valid"]:
        print(f"INVALID: {path}")

        for error in validation_report["errors"]:
            print(f"  ERROR: {error}")

        return 1

    frame = prepare_frame(path, contract_name)
    import_batch_id = str(frame.iloc[0]["import_batch_id"])
    file_hash = sha256_file(path)
    platform_id, platform_run_id = identify_platform(frame)

    contract_version = None

    if "contract_version" in frame.columns and not frame.empty:
        contract_version = str(frame.iloc[0]["contract_version"])

    started_at = utc_now()

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        if already_imported(connection, file_hash, contract_name):
            print(
                f"SKIPPED: {path.name} was already imported "
                f"for contract {contract_name}."
            )
            return 0

        connection.begin()

        try:
            connection.register("contract_frame", frame)

            column_names = list(frame.columns)
            quoted_columns = ", ".join(
                f'"{column}"' for column in column_names
            )

            connection.execute(
                f"""
                INSERT INTO contracts.{contract_name}
                ({quoted_columns})
                SELECT {quoted_columns}
                FROM contract_frame
                """
            )

            completed_at = utc_now()

            write_import_run(
                connection,
                {
                    "import_batch_id": import_batch_id,
                    "contract_name": contract_name,
                    "contract_version": contract_version,
                    "platform_id": platform_id,
                    "platform_run_id": platform_run_id,
                    "source_file": str(path.resolve()),
                    "source_file_sha256": file_hash,
                    "source_record_count": len(frame),
                    "imported_record_count": len(frame),
                    "rejected_record_count": 0,
                    "validation_status": "valid",
                    "import_status": "success",
                    "started_at_utc": started_at,
                    "completed_at_utc": completed_at,
                    "message": "Validated contract imported successfully",
                },
            )

            connection.unregister("contract_frame")
            connection.commit()

        except Exception as exc:
            connection.rollback()
            print(f"Import failed: {exc}", file=sys.stderr)
            return 1

    print(
        f"IMPORTED: {path.name} -> contracts.{contract_name} "
        f"({len(frame)} records)"
    )

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import one validated UIIP CSV contract."
    )

    parser.add_argument(
        "file",
        type=Path,
        help="CSV file to import",
    )

    parser.add_argument(
        "--contract",
        help="Explicit contract name",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.file.resolve()

    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2

    if not DATABASE_PATH.exists():
        print(
            "Integration database does not exist. "
            "Run initialize_integration_db.py first.",
            file=sys.stderr,
        )
        return 2

    contract_name = args.contract or infer_contract_name(path)

    return import_contract(path, contract_name)


if __name__ == "__main__":
    raise SystemExit(main())