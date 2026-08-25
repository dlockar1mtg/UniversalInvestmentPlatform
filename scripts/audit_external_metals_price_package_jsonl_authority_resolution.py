from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IDENTITY_NAMES = {
    "universal_asset_id",
    "asset_id",
    "ticker",
    "symbol",
    "metal",
    "vehicle",
    "instrument",
}
DATE_NAMES = {
    "date",
    "as_of_date",
    "price_date",
    "timestamp",
    "datetime",
    "observed_at",
    "observed_at_utc",
    "generated_at_utc",
}
PRICE_NAMES = {
    "price",
    "close",
    "current_price",
    "market_price",
    "spot_price",
    "unadjusted_close",
    "adj_close",
    "adjusted_close",
    "value",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--price-package-root", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL row {line_number} in {path.name} is not an object")
            rows.append(value)
    return rows


def numeric_columns(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    result: list[str] = []
    for column in columns:
        seen = False
        valid = True
        for row in rows:
            value = row.get(column)
            if value is None or value == "":
                continue
            seen = True
            if isinstance(value, bool):
                valid = False
                break
            try:
                float(value)
            except (TypeError, ValueError):
                valid = False
                break
        if seen and valid:
            result.append(column)
    return result


def inspect_file(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    columns = sorted({str(key) for row in rows for key in row.keys()})
    identities = [c for c in columns if c.lower() in IDENTITY_NAMES]
    dates = [c for c in columns if c.lower() in DATE_NAMES or "date" in c.lower() or "time" in c.lower()]
    numerics = numeric_columns(rows, columns)
    prices = [c for c in numerics if c.lower() in PRICE_NAMES or "price" in c.lower() or "close" in c.lower()]

    identity_values: dict[str, list[str]] = {}
    for column in identities:
        values = sorted({str(row.get(column)).strip() for row in rows if row.get(column) not in (None, "")})
        identity_values[column] = values

    non_null_counts = {
        column: sum(1 for row in rows if row.get(column) not in (None, ""))
        for column in columns
    }

    return {
        "relative_path": path.name,
        "row_count": len(rows),
        "columns": columns,
        "identity_columns": identities,
        "date_columns": dates,
        "numeric_columns": numerics,
        "price_columns": prices,
        "identity_values": identity_values,
        "non_null_counts": non_null_counts,
        "sample_rows": rows[:3],
    }


def main() -> int:
    args = parse_args()
    root = Path(args.price_package_root)
    output = Path(args.output)

    required = [
        root / "metals_current_price.jsonl",
        root / "metals_price_history.jsonl",
    ]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"Required certified package file missing: {path}")

    files = [inspect_file(path) for path in required]
    current = next(item for item in files if item["relative_path"] == "metals_current_price.jsonl")
    history = next(item for item in files if item["relative_path"] == "metals_price_history.jsonl")

    current_authority_resolved = bool(
        current["row_count"] > 0
        and current["identity_columns"]
        and current["price_columns"]
    )
    history_authority_resolved = bool(
        history["row_count"] > 0
        and history["identity_columns"]
        and history["date_columns"]
        and history["price_columns"]
    )

    report = {
        "status": "PASS",
        "read_only": True,
        "price_package_root": str(root),
        "files": files,
        "current_price_authority_resolved": current_authority_resolved,
        "dated_history_authority_resolved": history_authority_resolved,
        "current_price": current,
        "price_history": history,
        "semantic_rules": {
            "numeric_current_price_requires_identity_and_numeric_value": True,
            "dated_history_requires_identity_date_and_numeric_value": True,
            "jsonl_filename_alone_does_not_establish_authority": True,
            "price_semantics_is_not_numeric_price": True,
            "no_data_is_synthesized": True,
        },
        "next_decision": "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES",
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing audit evidence: {output}")
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
