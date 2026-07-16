from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CSV_SCHEMA_DIR = ROOT / "schemas" / "v1" / "csv"
JSON_SCHEMA_DIR = ROOT / "schemas" / "v1" / "json"

CONTRACT_VERSION = "1.0.0"


TYPE_MAP: dict[str, dict[str, Any]] = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "decimal": {"type": "number"},
    "boolean": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
    "timestamp": {"type": "string", "format": "date-time"},
}


ENUMS: dict[str, dict[str, list[Any]]] = {
    "platform_status": {
        "run_status": ["success", "partial", "failed", "running"],
    },
    "asset_master": {
        "asset_class": [
            "crypto",
            "equity",
            "etf",
            "metal",
            "commodity",
            "collectible",
            "real_estate",
            "cash",
            "bond",
            "macro_signal",
            "personal_finance",
        ],
        "liquidity_tier": ["high", "medium", "low", "illiquid"],
    },
    "recommendations": {
        "recommendation": [
            "strong_buy",
            "buy",
            "accumulate",
            "hold",
            "reduce",
            "sell",
            "strong_sell",
            "watch",
            "not_ready",
            "insufficient_data",
        ],
    },
    "risk_metrics": {
        "risk_level": ["low", "medium", "high", "extreme"],
    },
    "macro_signals": {
        "signal_direction": ["rising", "falling", "stable", "mixed"],
    },
    "export_manifest": {
        "file_format": ["csv", "parquet", "json"],
        "validation_status": [
            "not_validated",
            "valid",
            "warning",
            "invalid",
        ],
    },
}


RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "recommendations": {
        "normalized_score": (0, 100),
        "confidence_score": (0, 100),
        "target_weight": (0, 1),
        "minimum_weight": (0, 1),
        "maximum_weight": (0, 1),
    },
    "forecasts": {
        "probability_positive_return": (0, 1),
        "forecast_confidence": (0, 100),
    },
    "risk_metrics": {
        "risk_score": (0, 100),
        "liquidity_risk_score": (0, 100),
        "concentration_risk_score": (0, 100),
        "model_risk_score": (0, 100),
        "data_quality_score": (0, 100),
    },
    "portfolio_positions": {
        "current_weight": (0, 1),
        "target_weight": (0, 1),
        "minimum_weight": (0, 1),
        "maximum_weight": (0, 1),
    },
    "macro_signals": {
        "normalized_score": (0, 100),
        "confidence_score": (0, 100),
    },
}


PATTERNS: dict[str, dict[str, str]] = {
    "asset_master": {
        "universal_asset_id": r"^[a-z0-9]+(?:[:][a-z0-9-]+)+$",
    },
    "recommendations": {
        "universal_asset_id": r"^[a-z0-9]+(?:[:][a-z0-9-]+)+$",
    },
    "forecasts": {
        "universal_asset_id": r"^[a-z0-9]+(?:[:][a-z0-9-]+)+$",
    },
    "risk_metrics": {
        "universal_asset_id": r"^[a-z0-9]+(?:[:][a-z0-9-]+)+$",
    },
    "portfolio_positions": {
        "universal_asset_id": r"^[a-z0-9]+(?:[:][a-z0-9-]+)+$",
    },
}


def load_contract_definition(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def property_schema(
    contract_name: str,
    column: dict[str, str],
) -> dict[str, Any]:
    column_name = column["column_name"].strip()
    data_type = column["data_type"].strip().lower()

    if data_type not in TYPE_MAP:
        raise ValueError(
            f"Unsupported data type {data_type!r} "
            f"in {contract_name}.{column_name}"
        )

    schema = dict(TYPE_MAP[data_type])
    schema["description"] = column["description"].strip()

    example = column.get("example", "").strip()
    if example:
        schema["examples"] = [example]

    if column_name == "contract_version":
        schema["const"] = CONTRACT_VERSION

    enum_values = ENUMS.get(contract_name, {}).get(column_name)
    if enum_values:
        schema["enum"] = enum_values

    value_range = RANGES.get(contract_name, {}).get(column_name)
    if value_range:
        schema["minimum"], schema["maximum"] = value_range

    pattern = PATTERNS.get(contract_name, {}).get(column_name)
    if pattern:
        schema["pattern"] = pattern

    return schema


def generate_schema(path: Path) -> dict[str, Any]:
    contract_name = path.stem.removesuffix("_columns")
    columns = load_contract_definition(path)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for column in columns:
        column_name = column["column_name"].strip()
        properties[column_name] = property_schema(contract_name, column)

        if column["required"].strip().lower() == "yes":
            required.append(column_name)

    row_schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": (
            "https://uiip.local/schemas/v1/"
            f"{contract_name}.schema.json"
        ),
        "title": f"UIIP {contract_name.replace('_', ' ').title()} v1",
        "description": (
            f"One {contract_name} record conforming to "
            f"Universal Data Contracts {CONTRACT_VERSION}."
        ),
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }

    return row_schema


def main() -> None:
    JSON_SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

    definitions = sorted(CSV_SCHEMA_DIR.glob("*_columns.csv"))

    if not definitions:
        raise FileNotFoundError(
            f"No contract definitions found in {CSV_SCHEMA_DIR}"
        )

    generated = 0

    for definition in definitions:
        contract_name = definition.stem.removesuffix("_columns")
        output_path = JSON_SCHEMA_DIR / f"{contract_name}.schema.json"

        schema = generate_schema(definition)
        output_path.write_text(
            json.dumps(schema, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"Generated: {output_path.relative_to(ROOT)}")
        generated += 1

    print(f"\nGenerated {generated} JSON Schema files.")


if __name__ == "__main__":
    main()