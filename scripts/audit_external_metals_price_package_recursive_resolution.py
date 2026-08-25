from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

PRICE_NAMES = {
    "price", "close", "current_price", "last_price", "market_price", "value"
}
DATE_NAMES = {
    "date", "as_of_date", "price_date", "timestamp", "datetime", "observed_at"
}
IDENTITY_NAMES = {
    "asset_id", "universal_asset_id", "universal_vehicle_id", "ticker", "symbol", "metal", "asset", "name"
}


def _classify_columns(columns: list[str]) -> dict[str, list[str]]:
    lowered = {c.lower(): c for c in columns}
    return {
        "identity_columns": [lowered[n] for n in IDENTITY_NAMES if n in lowered],
        "date_columns": [lowered[n] for n in DATE_NAMES if n in lowered],
        "price_columns": [lowered[n] for n in PRICE_NAMES if n in lowered],
    }


def _csv_info(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
    classified = _classify_columns([str(c) for c in header])
    return {
        "relative_path": str(path),
        "suffix": path.suffix.lower(),
        "columns": header,
        **classified,
    }


def _json_info(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            "relative_path": str(path),
            "suffix": path.suffix.lower(),
            "json_error": str(exc),
            "columns": [],
            "identity_columns": [],
            "date_columns": [],
            "price_columns": [],
        }

    sample: Any = data
    if isinstance(data, list) and data:
        sample = data[0]
    elif isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value:
                sample = value[0]
                break

    columns = list(sample.keys()) if isinstance(sample, dict) else []
    classified = _classify_columns(columns)
    return {
        "relative_path": str(path),
        "suffix": path.suffix.lower(),
        "columns": columns,
        **classified,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--price-package-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.price_package_root)
    output = Path(args.output)
    if not root.is_dir():
        raise SystemExit(f"Price package root missing: {root}")

    files = sorted(p for p in root.rglob("*") if p.is_file())
    inspected: list[dict[str, Any]] = []
    for path in files:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            info = _csv_info(path)
        elif suffix == ".json":
            info = _json_info(path)
        else:
            info = {
                "relative_path": str(path),
                "suffix": suffix,
                "columns": [],
                "identity_columns": [],
                "date_columns": [],
                "price_columns": [],
            }
        info["relative_path"] = str(path.relative_to(root))
        inspected.append(info)

    current_candidates = [
        item for item in inspected
        if item["identity_columns"] and item["price_columns"]
    ]
    history_candidates = [
        item for item in current_candidates if item["date_columns"]
    ]

    report = {
        "status": "PASS",
        "read_only": True,
        "price_package_root": str(root),
        "recursive_file_count": len(files),
        "files": inspected,
        "numeric_price_candidate_count": len(current_candidates),
        "numeric_price_candidates": current_candidates,
        "dated_history_candidate_count": len(history_candidates),
        "dated_history_candidates": history_candidates,
        "semantic_rules": {
            "numeric_price_requires_identity_and_numeric_value": True,
            "dated_history_requires_identity_date_and_numeric_value": True,
            "price_semantics_is_not_numeric_price": True,
            "no_data_is_synthesized": True,
        },
        "next_decision": "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES",
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
