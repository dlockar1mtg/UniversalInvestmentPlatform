from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas" / "v1"
CSV_DEFINITION_DIR = SCHEMA_ROOT / "csv"
JSON_SCHEMA_DIR = SCHEMA_ROOT / "json"
DEFAULT_EXAMPLES_DIR = SCHEMA_ROOT / "examples"
REPORT_DIR = ROOT / "data" / "validation"

CONTRACT_VERSION = "1.0.0"

PRIMARY_KEYS: dict[str, list[str]] = {
    "platform_status": ["platform_id", "run_id"],
    "asset_master": [
        "platform_id",
        "run_id",
        "universal_asset_id",
    ],
    "recommendations": [
        "platform_id",
        "run_id",
        "universal_asset_id",
        "as_of_date",
        "time_horizon",
    ],
    "forecasts": [
        "platform_id",
        "run_id",
        "universal_asset_id",
        "forecast_horizon_months",
        "forecast_method",
        "scenario_name",
    ],
    "risk_metrics": [
        "platform_id",
        "run_id",
        "universal_asset_id",
        "as_of_date",
    ],
    "historical_performance": [
        "platform_id",
        "run_id",
        "universal_asset_id",
    ],
    "portfolio_positions": [
        "portfolio_id",
        "universal_asset_id",
        "as_of_date",
    ],
    "macro_signals": [
        "platform_id",
        "run_id",
        "signal_id",
        "as_of_date",
    ],
    "export_manifest": [
        "platform_id",
        "run_id",
        "export_name",
        "file_name",
    ],
}

IDENTIFIER_PATTERN = re.compile(
    r"^[a-z0-9]+(?:[:][a-z0-9-]+)+$"
)


class ValidationFailure(Exception):
    """Raised when validation cannot be performed."""


def load_column_definitions(
    contract_name: str,
) -> list[dict[str, str]]:
    path = CSV_DEFINITION_DIR / f"{contract_name}_columns.csv"

    if not path.exists():
        raise ValidationFailure(
            f"Column definition not found: {path}"
        )

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json_schema(contract_name: str) -> dict[str, Any]:
    path = JSON_SCHEMA_DIR / f"{contract_name}.schema.json"

    if not path.exists():
        raise ValidationFailure(
            f"JSON Schema not found: {path}. "
            "Run generate_json_schemas.py first."
        )

    return json.loads(path.read_text(encoding="utf-8"))


def parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes"}:
        return True

    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError(f"Invalid boolean value: {value!r}")


def convert_value(value: str, data_type: str) -> Any:
    value = value.strip()

    if value == "":
        return None

    if data_type == "string":
        return value

    if data_type == "integer":
        return int(value)

    if data_type == "decimal":
        number = float(value)

        if not math.isfinite(number):
            raise ValueError("Numeric value must be finite")

        return number

    if data_type == "boolean":
        return parse_boolean(value)

    if data_type == "date":
        date.fromisoformat(value)
        return value

    if data_type == "timestamp":
        normalized = value.replace("Z", "+00:00")
        datetime.fromisoformat(normalized)
        return value

    raise ValueError(f"Unsupported data type: {data_type}")


def convert_row(
    raw_row: dict[str, str],
    definitions: list[dict[str, str]],
) -> tuple[dict[str, Any], list[str]]:
    converted: dict[str, Any] = {}
    errors: list[str] = []

    definition_map = {
        item["column_name"]: item for item in definitions
    }

    for column_name, definition in definition_map.items():
        raw_value = raw_row.get(column_name, "")

        try:
            converted_value = convert_value(
                raw_value,
                definition["data_type"].strip().lower(),
            )
        except (ValueError, TypeError) as exc:
            errors.append(
                f"{column_name}: {exc}"
            )
            continue

        is_required = (
            definition["required"].strip().lower() == "yes"
        )

        if is_required and converted_value is None:
            errors.append(
                f"{column_name}: required value is missing"
            )
            continue

        if converted_value is not None:
            converted[column_name] = converted_value

    return converted, errors


def validate_headers(
    fieldnames: list[str] | None,
    definitions: list[dict[str, str]],
) -> list[str]:
    if fieldnames is None:
        return ["CSV has no header row"]

    expected = [item["column_name"] for item in definitions]
    expected_set = set(expected)
    actual_set = set(fieldnames)

    errors: list[str] = []

    missing = sorted(expected_set - actual_set)
    unexpected = sorted(actual_set - expected_set)

    if missing:
        errors.append(
            "Missing columns: " + ", ".join(missing)
        )

    if unexpected:
        errors.append(
            "Unexpected columns: " + ", ".join(unexpected)
        )

    if fieldnames != expected:
        errors.append(
            "Column order does not match the contract definition"
        )

    return errors


def validate_primary_keys(
    contract_name: str,
    rows: list[dict[str, Any]],
) -> list[str]:
    key_columns = PRIMARY_KEYS.get(contract_name)

    if not key_columns:
        return []

    keys: list[tuple[Any, ...]] = []

    for row in rows:
        key = tuple(row.get(column) for column in key_columns)
        keys.append(key)

    duplicates = [
        key
        for key, count in Counter(keys).items()
        if count > 1
    ]

    return [
        f"Duplicate logical primary key: {key}"
        for key in duplicates
    ]


def validate_business_rules(
    contract_name: str,
    row: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if row.get("contract_version") != CONTRACT_VERSION:
        errors.append(
            f"contract_version must equal {CONTRACT_VERSION}"
        )

    universal_asset_id = row.get("universal_asset_id")

    if universal_asset_id and not IDENTIFIER_PATTERN.fullmatch(
        universal_asset_id
    ):
        errors.append(
            "universal_asset_id does not follow the identifier standard"
        )

    minimum_weight = row.get("minimum_weight")
    target_weight = row.get("target_weight")
    maximum_weight = row.get("maximum_weight")

    if (
        minimum_weight is not None
        and target_weight is not None
        and minimum_weight > target_weight
    ):
        errors.append(
            "minimum_weight cannot exceed target_weight"
        )

    if (
        target_weight is not None
        and maximum_weight is not None
        and target_weight > maximum_weight
    ):
        errors.append(
            "target_weight cannot exceed maximum_weight"
        )

    if contract_name == "forecasts":
        origin = row.get("forecast_origin_date")
        endpoint = row.get("forecast_date")

        if origin and endpoint:
            if date.fromisoformat(endpoint) < date.fromisoformat(origin):
                errors.append(
                    "forecast_date cannot be earlier than "
                    "forecast_origin_date"
                )

    if contract_name == "historical_performance":
        eligible = row.get("performance_eligible")
        status = row.get("performance_status")
        suppression_reason = row.get("suppression_reason")

        start_date = row.get("historical_start_date")
        end_date = row.get("historical_end_date")
        start_value = row.get("historical_start_value")
        end_value = row.get("historical_end_value")
        elapsed_days = row.get("elapsed_days")
        observation_count = row.get("observation_count")
        distinct_date_count = row.get("distinct_date_count")
        source_count = row.get("source_count")

        if start_date and end_date:
            parsed_start = date.fromisoformat(start_date)
            parsed_end = date.fromisoformat(end_date)

            if parsed_end < parsed_start:
                errors.append(
                    "historical_end_date must be on or after "
                    "historical_start_date"
                )

            calculated_days = (parsed_end - parsed_start).days

            if (
                elapsed_days is not None
                and elapsed_days != calculated_days
            ):
                errors.append(
                    "elapsed_days must equal the difference between "
                    "historical_start_date and historical_end_date"
                )

        nonnegative_fields = {
            "historical_start_value": start_value,
            "historical_end_value": end_value,
            "elapsed_days": elapsed_days,
            "observation_count": observation_count,
            "distinct_date_count": distinct_date_count,
            "source_count": source_count,
            "minimum_value": row.get("minimum_value"),
            "maximum_value": row.get("maximum_value"),
        }

        for field_name, value in nonnegative_fields.items():
            if value is not None and value < 0:
                errors.append(
                    f"{field_name} must be greater than or equal to zero"
                )

        minimum_value = row.get("minimum_value")
        maximum_value = row.get("maximum_value")

        if (
            minimum_value is not None
            and maximum_value is not None
            and minimum_value > maximum_value
        ):
            errors.append(
                "minimum_value must be less than or equal to maximum_value"
            )

        if (
            observation_count is not None
            and distinct_date_count is not None
            and distinct_date_count > observation_count
        ):
            errors.append(
                "distinct_date_count may not exceed observation_count"
            )

        if eligible is True:
            required_evidence = {
                "historical_start_date": start_date,
                "historical_end_date": end_date,
                "historical_start_value": start_value,
                "historical_end_value": end_value,
                "elapsed_days": elapsed_days,
                "observation_count": observation_count,
                "distinct_date_count": distinct_date_count,
                "source_count": source_count,
            }

            missing_evidence = [
                field_name
                for field_name, value in required_evidence.items()
                if value is None
            ]

            if missing_evidence:
                errors.append(
                    "eligible historical performance requires: "
                    + ", ".join(missing_evidence)
                )

            if suppression_reason:
                errors.append(
                    "eligible historical performance may not have "
                    "a suppression_reason"
                )

            if status != "eligible":
                errors.append(
                    "performance_status must be eligible when "
                    "performance_eligible is true"
                )

        if eligible is False:
            if not suppression_reason:
                errors.append(
                    "suppressed historical performance requires "
                    "suppression_reason"
                )

            if status == "eligible":
                errors.append(
                    "performance_status may not be eligible when "
                    "performance_eligible is false"
                )

    if contract_name == "platform_status":
        status = row.get("run_status")
        completed = row.get("run_completed_at_utc")

        if status in {"success", "partial", "failed"} and not completed:
            errors.append(
                "completed runs require run_completed_at_utc"
            )

    return errors


def validate_csv(
    path: Path,
    contract_name: str,
) -> dict[str, Any]:
    definitions = load_column_definitions(contract_name)
    schema = load_json_schema(contract_name)

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    report: dict[str, Any] = {
        "file": str(path),
        "contract": contract_name,
        "valid": True,
        "record_count": 0,
        "errors": [],
        "warnings": [],
    }

    if not path.exists():
        report["valid"] = False
        report["errors"].append("File does not exist")
        return report

    converted_rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        header_errors = validate_headers(
            reader.fieldnames,
            definitions,
        )
        report["errors"].extend(header_errors)

        for row_number, raw_row in enumerate(reader, start=2):
            converted, conversion_errors = convert_row(
                raw_row,
                definitions,
            )

            for error in conversion_errors:
                report["errors"].append(
                    f"Row {row_number}: {error}"
                )

            if conversion_errors:
                continue

            schema_errors = sorted(
                validator.iter_errors(converted),
                key=lambda item: list(item.path),
            )

            for error in schema_errors:
                location = ".".join(
                    str(part) for part in error.path
                )
                prefix = f"{location}: " if location else ""
                report["errors"].append(
                    f"Row {row_number}: {prefix}{error.message}"
                )

            for error in validate_business_rules(
                contract_name,
                converted,
            ):
                report["errors"].append(
                    f"Row {row_number}: {error}"
                )

            converted_rows.append(converted)

    report["record_count"] = len(converted_rows)
    report["errors"].extend(
        validate_primary_keys(contract_name, converted_rows)
    )
    report["valid"] = not report["errors"]

    return report


def infer_contract_name(path: Path) -> str:
    name = path.stem

    if name.endswith("_example"):
        return name.removesuffix("_example")

    return name


def write_report(reports: list[dict[str, Any]]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORT_DIR / "phase_0_3_contract_validation.json"
    payload = {
        "contract_version": CONTRACT_VERSION,
        "generated_at_utc": (
            datetime.now().astimezone().isoformat()
        ),
        "valid": all(report["valid"] for report in reports),
        "reports": reports,
    }

    output_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate UIIP CSV exports."
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="CSV files to validate",
    )
    parser.add_argument(
        "--contract",
        help=(
            "Contract name when validating one explicitly named file, "
            "such as asset_master"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    files = args.files or sorted(
        DEFAULT_EXAMPLES_DIR.glob("*_example.csv")
    )

    if not files:
        print("No files were provided or discovered.", file=sys.stderr)
        return 2

    if args.contract and len(files) != 1:
        print(
            "--contract may only be used with one file.",
            file=sys.stderr,
        )
        return 2

    reports: list[dict[str, Any]] = []

    for path in files:
        contract_name = args.contract or infer_contract_name(path)
        report = validate_csv(path, contract_name)
        reports.append(report)

        status = "VALID" if report["valid"] else "INVALID"
        print(
            f"{status}: {path} "
            f"({report['record_count']} records)"
        )

        for error in report["errors"]:
            print(f"  ERROR: {error}")

        for warning in report["warnings"]:
            print(f"  WARNING: {warning}")

    output_path = write_report(reports)
    print(f"\nValidation report: {output_path}")

    return 0 if all(report["valid"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())