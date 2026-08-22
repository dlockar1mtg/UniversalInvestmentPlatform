from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import duckdb


FIELD_MAP = {
    "forecast_value_base": "point_forecast",
    "forecast_value_bear": "lower_bound",
    "forecast_value_bull": "upper_bound",
    "expected_total_return": "expected_return",
    "probability_positive_return": "probability_positive",
    "forecast_confidence": "confidence_score",
    "scenario_name": "scenario",
}


def _blank_to_none(value: object) -> object | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text == "" else text


def _load_package_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"Forecast package has no header: {path}")
        rows = [dict(row) for row in reader]
    if not rows:
        raise RuntimeError("Forecast package is empty.")
    return rows


def repair_forecast_alias_backfill(
    *,
    database_path: Path,
    package_path: Path,
    expected_package_id: str,
    expected_import_id: str,
    expected_row_count: int,
) -> dict[str, object]:
    forecasts_path = package_path / "forecasts.csv"
    if not forecasts_path.is_file():
        raise RuntimeError(f"Missing forecasts.csv: {forecasts_path}")

    package_rows = _load_package_rows(forecasts_path)
    if len(package_rows) != expected_row_count:
        raise RuntimeError(
            f"Expected {expected_row_count} package forecast rows; got {len(package_rows)}"
        )

    required_columns = {
        "universal_asset_id",
        "forecast_horizon_months",
        "forecast_method",
        *FIELD_MAP.keys(),
    }
    missing = required_columns - set(package_rows[0])
    if missing:
        raise RuntimeError(f"Forecast package missing columns: {sorted(missing)}")

    con = duckdb.connect(str(database_path))
    try:
        package = con.execute(
            """
            SELECT package_id, platform_id, package_path, successful_import_id
            FROM universal_packages
            WHERE package_id = ?
            """,
            [expected_package_id],
        ).fetchall()
        if len(package) != 1:
            raise RuntimeError("Expected package is not uniquely registered.")
        package_id, platform_id, registered_path, successful_import_id = package[0]
        if platform_id != "metals":
            raise RuntimeError(f"Expected Metals package; got {platform_id}")
        if str(successful_import_id) != expected_import_id:
            raise RuntimeError("Registered successful import ID does not match expectation.")
        if Path(str(registered_path)).resolve() != package_path.resolve():
            raise RuntimeError("Registered package path does not match repair package path.")

        health = con.execute(
            """
            SELECT health_status, registry_status, last_package_id, last_import_id,
                   last_import_status, warning_count, error_count
            FROM universal_import_health
            WHERE platform_id = 'metals'
            """
        ).fetchall()
        if len(health) != 1:
            raise RuntimeError("Expected exactly one Metals health row.")
        (
            health_status,
            registry_status,
            last_package_id,
            last_import_id,
            last_import_status,
            warning_count,
            error_count,
        ) = health[0]
        if health_status != "HEALTHY" or registry_status != "ACTIVE":
            raise RuntimeError("Metals is not in healthy/active state.")
        if str(last_package_id) != expected_package_id:
            raise RuntimeError("Expected package is not the current Metals package.")
        if str(last_import_id) != expected_import_id or last_import_status != "IMPORTED":
            raise RuntimeError("Expected import is not the current successful Metals import.")
        if int(warning_count or 0) != 0 or int(error_count or 0) != 0:
            raise RuntimeError("Current Metals health contains warnings or errors.")

        dataset = con.execute(
            """
            SELECT expected_row_count, imported_row_count, contract_status,
                   checksum_status, load_status, warning_count, error_count
            FROM universal_import_datasets
            WHERE import_id = ? AND dataset_name = 'forecasts'
            """,
            [expected_import_id],
        ).fetchall()
        if len(dataset) != 1:
            raise RuntimeError("Expected exactly one forecasts import-dataset row.")
        (
            expected_rows,
            imported_rows,
            contract_status,
            checksum_status,
            load_status,
            dataset_warnings,
            dataset_errors,
        ) = dataset[0]
        if int(expected_rows) != expected_row_count or int(imported_rows) != expected_row_count:
            raise RuntimeError("Forecast dataset row counts do not match expected authority.")
        if (contract_status, checksum_status, load_status) != ("PASS", "PASS", "IMPORTED"):
            raise RuntimeError("Forecast dataset did not pass contract/checksum/load gates.")
        if int(dataset_warnings or 0) != 0 or int(dataset_errors or 0) != 0:
            raise RuntimeError("Forecast dataset contains warnings or errors.")

        history_count = con.execute(
            """
            SELECT COUNT(*)
            FROM forecasts_history
            WHERE platform_id = 'metals' AND _package_id = ? AND _import_id = ?
            """,
            [expected_package_id, expected_import_id],
        ).fetchone()[0]
        if int(history_count) != expected_row_count:
            raise RuntimeError(
                f"Expected {expected_row_count} forecast history rows; got {history_count}"
            )

        updates: list[tuple[object, ...]] = []
        populated_source_counts = {destination: 0 for destination in FIELD_MAP.values()}

        for source in package_rows:
            asset_id = str(source["universal_asset_id"]).strip()
            horizon = int(str(source["forecast_horizon_months"]).strip())
            method = str(source["forecast_method"]).strip()

            existing = con.execute(
                """
                SELECT point_forecast, lower_bound, upper_bound, expected_return,
                       probability_positive, confidence_score, scenario
                FROM forecasts_history
                WHERE platform_id = 'metals'
                  AND _package_id = ?
                  AND _import_id = ?
                  AND universal_asset_id = ?
                  AND forecast_horizon_months = ?
                  AND forecast_method = ?
                """,
                [expected_package_id, expected_import_id, asset_id, horizon, method],
            ).fetchall()
            if len(existing) != 1:
                raise RuntimeError(
                    f"Forecast row is not uniquely addressable: {asset_id}/{horizon}/{method}"
                )

            current_values = dict(zip(FIELD_MAP.values(), existing[0], strict=True))
            replacement: dict[str, object | None] = {}
            for source_column, destination_column in FIELD_MAP.items():
                source_value = _blank_to_none(source.get(source_column))
                current_value = current_values[destination_column]
                if source_value is not None:
                    populated_source_counts[destination_column] += 1
                    if current_value is not None and str(current_value) != str(source_value):
                        raise RuntimeError(
                            f"Refusing to overwrite non-null {destination_column} for "
                            f"{asset_id}/{horizon}: db={current_value!r} source={source_value!r}"
                        )
                replacement[destination_column] = (
                    current_value if current_value is not None else source_value
                )

            updates.append(
                (
                    replacement["point_forecast"],
                    replacement["lower_bound"],
                    replacement["upper_bound"],
                    replacement["expected_return"],
                    replacement["probability_positive"],
                    replacement["confidence_score"],
                    replacement["scenario"],
                    expected_package_id,
                    expected_import_id,
                    asset_id,
                    horizon,
                    method,
                )
            )

        if populated_source_counts["expected_return"] != expected_row_count:
            raise RuntimeError("Not every package row has expected_total_return authority.")
        if populated_source_counts["probability_positive"] != expected_row_count:
            raise RuntimeError("Not every package row has probability_positive_return authority.")
        if populated_source_counts["confidence_score"] != expected_row_count:
            raise RuntimeError("Not every package row has forecast_confidence authority.")

        con.execute("BEGIN TRANSACTION")
        try:
            con.executemany(
                """
                UPDATE forecasts_history
                SET point_forecast = ?,
                    lower_bound = ?,
                    upper_bound = ?,
                    expected_return = ?,
                    probability_positive = ?,
                    confidence_score = ?,
                    scenario = ?
                WHERE _package_id = ?
                  AND _import_id = ?
                  AND universal_asset_id = ?
                  AND forecast_horizon_months = ?
                  AND forecast_method = ?
                """,
                updates,
            )

            post = con.execute(
                """
                SELECT COUNT(*) AS total,
                       COUNT(expected_return) AS expected_return_populated,
                       COUNT(probability_positive) AS probability_positive_populated,
                       COUNT(confidence_score) AS confidence_score_populated,
                       COUNT(point_forecast) AS point_forecast_populated,
                       COUNT(lower_bound) AS lower_bound_populated,
                       COUNT(upper_bound) AS upper_bound_populated,
                       COUNT(scenario) AS scenario_populated
                FROM forecasts_history
                WHERE platform_id = 'metals' AND _package_id = ? AND _import_id = ?
                """,
                [expected_package_id, expected_import_id],
            ).fetchone()
            if int(post[0]) != expected_row_count:
                raise RuntimeError("Post-repair row count changed unexpectedly.")
            if int(post[1]) != expected_row_count:
                raise RuntimeError("Expected-return repair is incomplete.")
            if int(post[2]) != expected_row_count:
                raise RuntimeError("Positive-probability repair is incomplete.")
            if int(post[3]) != expected_row_count:
                raise RuntimeError("Confidence repair is incomplete.")

            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        return {
            "status": "PASS",
            "package_id": expected_package_id,
            "import_id": expected_import_id,
            "row_count": expected_row_count,
            "populated_source_counts": populated_source_counts,
            "post_repair": {
                "expected_return_populated": int(post[1]),
                "probability_positive_populated": int(post[2]),
                "confidence_score_populated": int(post[3]),
                "point_forecast_populated": int(post[4]),
                "lower_bound_populated": int(post[5]),
                "upper_bound_populated": int(post[6]),
                "scenario_populated": int(post[7]),
            },
            "synthetic_values_created": False,
            "native_model_rerun": False,
            "source_refresh": False,
        }
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--package-path", required=True, type=Path)
    parser.add_argument("--expected-package-id", required=True)
    parser.add_argument("--expected-import-id", required=True)
    parser.add_argument("--expected-row-count", required=True, type=int)
    args = parser.parse_args()

    result = repair_forecast_alias_backfill(
        database_path=args.database,
        package_path=args.package_path,
        expected_package_id=args.expected_package_id,
        expected_import_id=args.expected_import_id,
        expected_row_count=args.expected_row_count,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
