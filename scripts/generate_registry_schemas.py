from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFINITION_DIR = ROOT / "registry" / "v1" / "schemas"
OUTPUT_DIR = ROOT / "registry" / "v1" / "schemas"

REGISTRY_VERSION = "1.0.0"


TYPE_MAP: dict[str, dict[str, Any]] = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "decimal": {"type": "number"},
    "boolean": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
    "timestamp": {"type": "string", "format": "date-time"},
}


ENUMS: dict[str, dict[str, list[str]]] = {
    "platform_registry": {
        "platform_status": [
            "operational",
            "partially_operational",
            "development",
            "planning",
            "not_started",
            "blocked",
            "unavailable",
            "archived",
        ],
        "integration_stage": [
            "not_started",
            "inventory",
            "baseline_frozen",
            "documented",
            "adapter_development",
            "export_ready",
            "registered",
            "integrated",
            "validated",
            "production",
        ],
        "expected_refresh_frequency": [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "manual",
            "event_driven",
            "not_applicable",
        ],
    },
    "machine_registry": {
        "machine_role": [
            "primary_workstation",
            "secondary_laptop",
            "cloud_worker",
            "external_service",
            "not_assigned",
        ],
        "availability_status": [
            "available",
            "unavailable",
            "limited",
            "not_configured",
        ],
    },
}


PATTERNS: dict[str, dict[str, str]] = {
    "platform_registry": {
        "platform_id": r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        "machine_id": r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    },
    "machine_registry": {
        "machine_id": r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    },
}


def load_definition(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_property(
    registry_name: str,
    column: dict[str, str],
) -> dict[str, Any]:
    column_name = column["column_name"].strip()
    data_type = column["data_type"].strip().lower()

    if data_type not in TYPE_MAP:
        raise ValueError(
            f"Unsupported type {data_type!r} "
            f"in {registry_name}.{column_name}"
        )

    schema = dict(TYPE_MAP[data_type])
    schema["description"] = column["description"].strip()

    if column_name == "registry_version":
        schema["const"] = REGISTRY_VERSION

    enum_values = ENUMS.get(registry_name, {}).get(column_name)
    if enum_values:
        schema["enum"] = enum_values

    pattern = PATTERNS.get(registry_name, {}).get(column_name)
    if pattern:
        schema["pattern"] = pattern

    if data_type == "integer":
        schema["minimum"] = 0

    return schema


def generate_schema(path: Path) -> dict[str, Any]:
    registry_name = path.stem.removesuffix("_columns")
    columns = load_definition(path)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for column in columns:
        column_name = column["column_name"].strip()
        properties[column_name] = build_property(
            registry_name,
            column,
        )

        if column["required"].strip().lower() == "yes":
            required.append(column_name)

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": (
            "https://uiip.local/registry/v1/"
            f"{registry_name}.schema.json"
        ),
        "title": f"UIIP {registry_name.replace('_', ' ').title()}",
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def main() -> None:
    definition_files = sorted(
        DEFINITION_DIR.glob("*_columns.csv")
    )

    if not definition_files:
        raise FileNotFoundError(
            f"No registry definitions found in {DEFINITION_DIR}"
        )

    generated = 0

    for definition in definition_files:
        registry_name = definition.stem.removesuffix("_columns")
        output_path = (
            OUTPUT_DIR / f"{registry_name}.schema.json"
        )

        schema = generate_schema(definition)
        output_path.write_text(
            json.dumps(schema, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"Generated: {output_path.relative_to(ROOT)}")
        generated += 1

    print(f"\nGenerated {generated} registry schemas.")


if __name__ == "__main__":
    main()