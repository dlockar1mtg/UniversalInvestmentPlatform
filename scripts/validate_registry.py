from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = ROOT / "registry" / "v1"
SCHEMA_DIR = REGISTRY_ROOT / "schemas"
DATA_DIR = REGISTRY_ROOT / "data"
REPORT_DIR = ROOT / "data" / "validation"

REGISTRY_VERSION = "1.0.0"


TYPE_MAP = {
    "string": str,
    "integer": int,
    "decimal": float,
    "boolean": bool,
    "date": str,
    "timestamp": str,
}


def load_definitions(name: str) -> list[dict[str, str]]:
    path = SCHEMA_DIR / f"{name}_columns.csv"

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / f"{name}.schema.json"
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
        return float(value)

    if data_type == "boolean":
        return parse_boolean(value)

    if data_type == "date":
        date.fromisoformat(value)
        return value

    if data_type == "timestamp":
        datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return value

    raise ValueError(f"Unsupported type: {data_type}")


def read_registry(
    name: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    definitions = load_definitions(name)
    data_path = DATA_DIR / f"{name}.csv"

    errors: list[str] = []
    records: list[dict[str, Any]] = []

    expected_columns = [
        definition["column_name"]
        for definition in definitions
    ]

    definition_map = {
        definition["column_name"]: definition
        for definition in definitions
    }

    with data_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames != expected_columns:
            errors.append(
                f"{name}: column order or names do not "
                "match the registry definition"
            )

        for row_number, row in enumerate(reader, start=2):
            converted: dict[str, Any] = {}

            for column_name, definition in definition_map.items():
                raw_value = row.get(column_name, "")

                try:
                    value = convert_value(
                        raw_value,
                        definition["data_type"].strip().lower(),
                    )
                except (TypeError, ValueError) as exc:
                    errors.append(
                        f"{name} row {row_number} "
                        f"{column_name}: {exc}"
                    )
                    continue

                required = (
                    definition["required"].strip().lower()
                    == "yes"
                )

                if required and value is None:
                    errors.append(
                        f"{name} row {row_number} "
                        f"{column_name}: required value missing"
                    )
                    continue

                if value is not None:
                    converted[column_name] = value

            records.append(converted)

    return records, errors


def validate_schema(
    name: str,
    records: list[dict[str, Any]],
) -> list[str]:
    schema = load_schema(name)
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    errors: list[str] = []

    for row_number, record in enumerate(records, start=2):
        for error in validator.iter_errors(record):
            location = ".".join(
                str(item) for item in error.path
            )
            prefix = f"{location}: " if location else ""

            errors.append(
                f"{name} row {row_number}: "
                f"{prefix}{error.message}"
            )

    return errors


def duplicate_errors(
    name: str,
    records: list[dict[str, Any]],
    key: str,
) -> list[str]:
    seen: set[Any] = set()
    errors: list[str] = []

    for record in records:
        value = record.get(key)

        if value in seen:
            errors.append(
                f"{name}: duplicate {key} {value!r}"
            )

        seen.add(value)

    return errors


def cross_registry_errors(
    platforms: list[dict[str, Any]],
    machines: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []

    machine_ids = {
        machine["machine_id"]
        for machine in machines
        if "machine_id" in machine
    }

    for platform in platforms:
        machine_id = platform.get("machine_id")

        if machine_id not in machine_ids:
            errors.append(
                f"platform {platform.get('platform_id')!r} "
                f"references unknown machine {machine_id!r}"
            )

        exchange_folder = platform.get("exchange_folder")

        if exchange_folder:
            exchange_path = ROOT / exchange_folder

            if (
                platform.get("is_enabled")
                and not exchange_path.exists()
            ):
                errors.append(
                    f"platform {platform.get('platform_id')!r} "
                    f"references missing exchange folder "
                    f"{exchange_folder!r}"
                )

    return errors


def build_health_rows(
    platforms: list[dict[str, Any]],
    machines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    machine_map = {
        machine["machine_id"]: machine
        for machine in machines
    }

    now = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []

    for platform in platforms:
        health_status = "unknown"
        health_reason = "No health rule matched"

        machine = machine_map.get(platform["machine_id"])

        if not platform.get("is_enabled", False):
            health_status = "not_configured"
            health_reason = "Platform is disabled in registry"

        elif platform["platform_status"] == "blocked":
            health_status = "blocked"
            health_reason = platform.get(
                "known_issue",
                "Platform status is blocked",
            )

        elif not machine:
            health_status = "unavailable"
            health_reason = "Assigned machine is not registered"

        elif machine["availability_status"] == "unavailable":
            health_status = "unavailable"
            health_reason = "Assigned machine is unavailable"

        elif not platform.get("local_path"):
            health_status = "warning"
            health_reason = "Local repository path is not configured"

        elif not Path(platform["local_path"]).exists():
            health_status = "unavailable"
            health_reason = "Configured local path does not exist"

        elif platform.get("last_successful_run_at_utc"):
            last_run = datetime.fromisoformat(
                platform["last_successful_run_at_utc"].replace(
                    "Z",
                    "+00:00",
                )
            )

            threshold = platform.get(
                "freshness_threshold_hours"
            )

            if threshold is not None:
                age_hours = (
                    now - last_run.astimezone(timezone.utc)
                ).total_seconds() / 3600

                if age_hours > threshold:
                    health_status = "stale"
                    health_reason = (
                        f"Last successful run is "
                        f"{age_hours:.1f} hours old"
                    )
                else:
                    health_status = "healthy"
                    health_reason = "Platform is within freshness threshold"
            else:
                health_status = "healthy"
                health_reason = "Platform path and machine are available"

        elif platform["integration_stage"] in {
            "not_started",
            "inventory",
            "baseline_frozen",
            "documented",
        }:
            health_status = "warning"
            health_reason = (
                "Platform has not published an integrated run yet"
            )

        else:
            health_status = "unknown"
            health_reason = "No successful run timestamp is available"

        rows.append(
            {
                "platform_id": platform["platform_id"],
                "platform_name": platform["platform_name"],
                "platform_status": platform["platform_status"],
                "integration_stage": platform["integration_stage"],
                "machine_id": platform["machine_id"],
                "health_status": health_status,
                "health_reason": health_reason,
                "evaluated_at_utc": now.isoformat(),
            }
        )

    return rows


def write_report(
    valid: bool,
    errors: list[str],
    platform_count: int,
    machine_count: int,
    health_rows: list[dict[str, Any]],
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = REPORT_DIR / "phase_0_4_registry_validation.json"

    payload = {
        "registry_version": REGISTRY_VERSION,
        "valid": valid,
        "platform_count": platform_count,
        "machine_count": machine_count,
        "errors": errors,
        "health": health_rows,
    }

    output_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    platform_records, platform_errors = read_registry(
        "platform_registry"
    )
    machine_records, machine_errors = read_registry(
        "machine_registry"
    )

    errors = [
        *platform_errors,
        *machine_errors,
        *validate_schema(
            "platform_registry",
            platform_records,
        ),
        *validate_schema(
            "machine_registry",
            machine_records,
        ),
        *duplicate_errors(
            "platform_registry",
            platform_records,
            "platform_id",
        ),
        *duplicate_errors(
            "machine_registry",
            machine_records,
            "machine_id",
        ),
        *cross_registry_errors(
            platform_records,
            machine_records,
        ),
    ]

    health_rows = build_health_rows(
        platform_records,
        machine_records,
    )

    valid = not errors

    report_path = write_report(
        valid=valid,
        errors=errors,
        platform_count=len(platform_records),
        machine_count=len(machine_records),
        health_rows=health_rows,
    )

    print(
        f"Platforms validated: {len(platform_records)}"
    )
    print(
        f"Machines validated: {len(machine_records)}"
    )

    for health in health_rows:
        print(
            f"{health['platform_id']}: "
            f"{health['health_status']} — "
            f"{health['health_reason']}"
        )

    if errors:
        print("\nRegistry validation failed:")

        for error in errors:
            print(f"  ERROR: {error}")
    else:
        print("\nRegistry validation passed.")

    print(f"\nValidation report: {report_path}")

    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())