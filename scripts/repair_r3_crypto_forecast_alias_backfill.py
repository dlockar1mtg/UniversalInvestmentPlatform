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


def _source_identity(row: dict[str, str]) -> tuple[str, int, str]:
    asset_id = str(row["universal_asset_id"]).strip()
    horizon = int(str(row["forecast_horizon_months"]).strip())
    method = str(row["forecast_method"]).strip()
    if not asset_id or not method:
        raise RuntimeError("Forecast package contains blank governed identity fields.")
    return asset_id, horizon, method


def repair_crypto_forecast_alias_backfill(*, database_path: Path) -> dict[str, object]:
    database_path = database_path.resolve()
    if not database_path.is_file():
        raise RuntimeError(f"UIP database not found: {database_path}")

    con = duckdb.connect(str(database_path))
    try:
        health = con.execute(
            """
            SELECT health_status, registry_status, last_package_id, last_import_id,
                   last_import_status, warning_count, error_count
            FROM universal_import_health
            WHERE lower(platform_id) = 'crypto'
            """
        ).fetchall()
        if len(health) != 1:
            raise RuntimeError("Expected exactly one Crypto import-health row.")

        (
            health_status,
            registry_status,
            package_id,
            import_id,
            import_status,
            warning_count,
            error_count,
        ) = health[0]

        if health_status != "HEALTHY" or registry_status != "ACTIVE":
            raise RuntimeError("Crypto is not in HEALTHY/ACTIVE import state.")
        if import_status != "IMPORTED":
            raise RuntimeError("Current Crypto import is not IMPORTED.")
        if int(warning_count or 0) != 0 or int(error_count or 0) != 0:
            raise RuntimeError("Current Crypto import health contains warnings or errors.")
        if not package_id or not import_id:
            raise RuntimeError("Current Crypto package/import identity is missing.")

        package = con.execute(
            """
            SELECT package_path, successful_import_id
            FROM universal_packages
            WHERE package_id = ? AND lower(platform_id) = 'crypto'
            """,
            [package_id],
        ).fetchall()
        if len(package) != 1:
            raise RuntimeError("Current Crypto package is not uniquely registered.")

        package_path = Path(str(package[0][0])).resolve()
        successful_import_id = str(package[0][1])
        if successful_import_id != str(import_id):
            raise RuntimeError("Crypto package successful import does not match current import.")
        if not package_path.is_dir():
            raise RuntimeError(f"Registered Crypto package path is missing: {package_path}")

        forecasts_path = package_path / "forecasts.csv"
        if not forecasts_path.is_file():
            raise RuntimeError(f"Missing Crypto forecasts.csv: {forecasts_path}")

        dataset = con.execute(
            """
            SELECT expected_row_count, imported_row_count, contract_status,
                   checksum_status, load_status, warning_count, error_count
            FROM universal_import_datasets
            WHERE import_id = ? AND dataset_name = 'forecasts'
            """,
            [import_id],
        ).fetchall()
        if len(dataset) != 1:
            raise RuntimeError("Expected exactly one Crypto forecasts import-dataset row.")

        (
            expected_rows,
            imported_rows,
            contract_status,
            checksum_status,
            load_status,
            dataset_warnings,
            dataset_errors,
        ) = dataset[0]

        if (contract_status, checksum_status, load_status) != ("PASS", "PASS", "IMPORTED"):
            raise RuntimeError("Crypto forecast dataset did not pass contract/checksum/load gates.")
        if int(dataset_warnings or 0) != 0 or int(dataset_errors or 0) != 0:
            raise RuntimeError("Crypto forecast dataset contains warnings or errors.")

        package_rows = _load_package_rows(forecasts_path)
        expected_row_count = int(expected_rows)
        if int(imported_rows) != expected_row_count:
            raise RuntimeError("Crypto forecast expected/imported row counts disagree.")
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
            raise RuntimeError(f"Crypto forecast package missing columns: {sorted(missing)}")

        source_keys = [_source_identity(row) for row in package_rows]
        if len(set(source_keys)) != len(source_keys):
            raise RuntimeError("Crypto forecast package contains duplicate asset/horizon/method keys.")

        history_count = int(
            con.execute(
                """
                SELECT COUNT(*)
                FROM forecasts_history
                WHERE lower(platform_id) = 'crypto'
                  AND _package_id = ?
                  AND _import_id = ?
                """,
                [package_id, import_id],
            ).fetchone()[0]
        )
        if history_count != expected_row_count:
            raise RuntimeError(
                f"Expected {expected_row_count} Crypto forecast history rows; got {history_count}"
            )

        source_populated_counts = {destination: 0 for destination in FIELD_MAP.values()}
        pre_populated_counts = dict(
            zip(
                FIELD_MAP.values(),
                con.execute(
                    """
                    SELECT COUNT(point_forecast), COUNT(lower_bound), COUNT(upper_bound),
                           COUNT(expected_return), COUNT(probability_positive),
                           COUNT(confidence_score), COUNT(scenario)
                    FROM forecasts_history
                    WHERE lower(platform_id) = 'crypto'
                      AND _package_id = ?
                      AND _import_id = ?
                    """,
                    [package_id, import_id],
                ).fetchone(),
                strict=True,
            )
        )

        updates: list[tuple[object, ...]] = []
        for source in package_rows:
            asset_id, horizon, method = _source_identity(source)
            existing = con.execute(
                """
                SELECT point_forecast, lower_bound, upper_bound, expected_return,
                       probability_positive, confidence_score, scenario
                FROM forecasts_history
                WHERE lower(platform_id) = 'crypto'
                  AND _package_id = ?
                  AND _import_id = ?
                  AND universal_asset_id = ?
                  AND forecast_horizon_months = ?
                  AND forecast_method = ?
                """,
                [package_id, import_id, asset_id, horizon, method],
            ).fetchall()
            if len(existing) != 1:
                raise RuntimeError(
                    f"Crypto forecast row is not uniquely addressable: {asset_id}/{horizon}/{method}"
                )

            current_values = dict(zip(FIELD_MAP.values(), existing[0], strict=True))
            replacement: dict[str, object | None] = {}
            for source_column, destination_column in FIELD_MAP.items():
                source_value = _blank_to_none(source.get(source_column))
                current_value = current_values[destination_column]
                if source_value is not None:
                    source_populated_counts[destination_column] += 1
                    if current_value is not None and str(current_value) != str(source_value):
                        raise RuntimeError(
                            f"Refusing to overwrite non-null {destination_column} for "
                            f"{asset_id}/{horizon}/{method}: db={current_value!r} source={source_value!r}"
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
                    package_id,
                    import_id,
                    asset_id,
                    horizon,
                    method,
                )
            )

        if not any(source_populated_counts.values()):
            raise RuntimeError("Crypto package contains no populated forecast alias authority to recover.")

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
                SELECT COUNT(point_forecast), COUNT(lower_bound), COUNT(upper_bound),
                       COUNT(expected_return), COUNT(probability_positive),
                       COUNT(confidence_score), COUNT(scenario)
                FROM forecasts_history
                WHERE lower(platform_id) = 'crypto'
                  AND _package_id = ?
                  AND _import_id = ?
                """,
                [package_id, import_id],
            ).fetchone()
            post_populated_counts = dict(zip(FIELD_MAP.values(), post, strict=True))

            for destination in FIELD_MAP.values():
                expected_populated = max(
                    int(pre_populated_counts[destination]),
                    int(source_populated_counts[destination]),
                )
                if int(post_populated_counts[destination]) != expected_populated:
                    raise RuntimeError(
                        f"Post-repair {destination} count mismatch: "
                        f"expected {expected_populated}, got {post_populated_counts[destination]}"
                    )

            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        return {
            "status": "PASS",
            "platform_id": "crypto",
            "package_id": str(package_id),
            "import_id": str(import_id),
            "package_path": str(package_path),
            "forecast_row_count": expected_row_count,
            "source_populated_counts": {
                key: int(value) for key, value in source_populated_counts.items()
            },
            "pre_populated_counts": {
                key: int(value) for key, value in pre_populated_counts.items()
            },
            "post_populated_counts": {
                key: int(value) for key, value in post_populated_counts.items()
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
    args = parser.parse_args()
    result = repair_crypto_forecast_alias_backfill(database_path=args.database)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
