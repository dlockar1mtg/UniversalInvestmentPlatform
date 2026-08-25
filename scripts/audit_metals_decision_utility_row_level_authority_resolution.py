from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def _nonblank(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _table_exists(connection: duckdb.DuckDBPyConnection, name: str) -> bool:
    row = connection.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main' AND table_name=?",
        [name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def _rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    cursor = connection.execute(sql)
    names = [str(item[0]) for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _forecast_summary(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    if not _table_exists(connection, "forecasts_current"):
        return {"table_present": False}
    rows = _rows(
        connection,
        """
        SELECT universal_asset_id, forecast_horizon_months, forecast_method,
               point_forecast, lower_bound, upper_bound, expected_return,
               confidence_score, scenario, forecast_origin_date
        FROM forecasts_current
        WHERE universal_asset_id LIKE 'metals:%'
        ORDER BY universal_asset_id, forecast_horizon_months, forecast_method
        """,
    )
    by_asset: dict[str, dict[str, Any]] = {}
    for row in rows:
        asset = str(row.get("universal_asset_id") or "")
        item = by_asset.setdefault(
            asset,
            {
                "asset_id": asset,
                "asset_kind": "commodity" if ":commodity:" in asset else "vehicle" if ":vehicle:" in asset else "other",
                "row_count": 0,
                "non_null_point_forecast": 0,
                "non_null_lower_bound": 0,
                "non_null_upper_bound": 0,
                "non_null_expected_return": 0,
                "horizons": [],
            },
        )
        item["row_count"] += 1
        if row.get("point_forecast") is not None:
            item["non_null_point_forecast"] += 1
        if row.get("lower_bound") is not None:
            item["non_null_lower_bound"] += 1
        if row.get("upper_bound") is not None:
            item["non_null_upper_bound"] += 1
        if row.get("expected_return") is not None:
            item["non_null_expected_return"] += 1
        horizon = row.get("forecast_horizon_months")
        if horizon is not None and horizon not in item["horizons"]:
            item["horizons"].append(horizon)
    return {
        "table_present": True,
        "metals_row_count": len(rows),
        "asset_count": len(by_asset),
        "assets": list(by_asset.values()),
    }


def _recommendation_summary(connection: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    if not _table_exists(connection, "recommendations_current"):
        return {"table_present": False}
    rows = _rows(
        connection,
        """
        SELECT universal_asset_id, recommendation, normalized_score, confidence_score,
               rationale, risk_summary, time_horizon_months
        FROM recommendations_current
        WHERE universal_asset_id LIKE 'metals:%'
        ORDER BY universal_asset_id
        """,
    )
    return {
        "table_present": True,
        "metals_row_count": len(rows),
        "rationale_nonblank_count": sum(1 for row in rows if _nonblank(row.get("rationale"))),
        "risk_summary_nonblank_count": sum(1 for row in rows if _nonblank(row.get("risk_summary"))),
        "time_horizon_non_null_count": sum(1 for row in rows if row.get("time_horizon_months") is not None),
        "rows": rows,
    }


def _csv_inventory(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        return {"root_present": False, "files": []}
    files = []
    price_names = {"price", "close", "current_price", "value", "last", "settle"}
    date_names = {"date", "as_of_date", "observation_date", "timestamp", "datetime", "time"}
    identity_names = {"asset_id", "universal_asset_id", "ticker", "symbol", "series_key", "metal"}
    for path in sorted(root.rglob("*.csv")):
        try:
            frame = pd.read_csv(path, nrows=5)
        except Exception as exc:
            files.append({"path": str(path), "read_error": str(exc)})
            continue
        columns = [str(column) for column in frame.columns]
        lowered = {column.lower(): column for column in columns}
        price_columns = [lowered[name] for name in price_names if name in lowered]
        date_columns = [lowered[name] for name in date_names if name in lowered]
        identity_columns = [lowered[name] for name in identity_names if name in lowered]
        files.append(
            {
                "path": str(path),
                "columns": columns,
                "price_columns": sorted(price_columns),
                "date_columns": sorted(date_columns),
                "identity_columns": sorted(identity_columns),
                "candidate_numeric_current_price": bool(price_columns and identity_columns),
                "candidate_dated_price_history": bool(price_columns and date_columns and identity_columns),
            }
        )
    return {
        "root_present": True,
        "file_count": len(files),
        "files": files,
        "current_price_candidate_count": sum(1 for item in files if item.get("candidate_numeric_current_price")),
        "dated_history_candidate_count": sum(1 for item in files if item.get("candidate_dated_price_history")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--price-package-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database = Path(args.database).resolve()
    package_root = Path(args.price_package_root).resolve()
    output = Path(args.output).resolve()
    connection = duckdb.connect(str(database), read_only=True)
    try:
        report = {
            "status": "PASS",
            "read_only": True,
            "database": str(database),
            "price_package_root": str(package_root),
            "forecasts_current_metals": _forecast_summary(connection),
            "recommendations_current_metals": _recommendation_summary(connection),
            "external_price_history_inventory": _csv_inventory(package_root),
            "semantic_rules": {
                "forecast_bounds_require_non_null_row_level_values": True,
                "recommendation_rationale_requires_asset_identity_and_non_blank_text": True,
                "external_price_requires_identity_date_and_numeric_value": True,
                "price_semantics_is_not_numeric_price": True,
                "downside_penalty_is_not_forecast_lower_bound": True,
                "uncertainty_penalty_is_not_generic_risk_score": True,
                "no_data_is_synthesized": True,
            },
            "next_decision": "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES",
        }
    finally:
        connection.close()

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RuntimeError(f"Output already exists and will not be overwritten: {output}")
    output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
