from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import duckdb

EXPECTED_COUNTS = {
    "components": 64,
    "regimes": 12,
    "adjusted": 32,
    "changes": 10,
    "freshness": 21,
    "health": 1,
}

EXPECTED_PACKAGE_ID = "metals-20260728T182311Z-5da5336b"
EXPECTED_IMPORT_ID = "14cfce16-f806-4db1-9303-210de844c194"
EXPECTED_MANIFEST_SHA256 = "f48de30a6f58742a1b1a3554464af320150cd983ded144c6df4c9b8504c7f4e5"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_rows(connection: duckdb.DuckDBPyConnection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def distinct_lineage(connection: duckdb.DuckDBPyConnection, table: str) -> dict[str, list[str | None]]:
    rows = connection.execute(
        f"""
        SELECT DISTINCT _package_id, _import_id, _manifest_sha256
        FROM {table}
        ORDER BY 1, 2, 3
        """
    ).fetchall()
    return {
        "package_ids": sorted({str(row[0]) for row in rows if row[0] is not None}),
        "import_ids": sorted({str(row[1]) for row in rows if row[1] is not None}),
        "manifest_sha256": sorted({str(row[2]) for row in rows if row[2] is not None}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify production Metals tactical evidence authority read-only.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()

    before = sha256_file(args.database)
    expected_sha = args.expected_sha256.lower()
    if before.lower() != expected_sha:
        raise RuntimeError(f"Database SHA-256 mismatch: {before}")

    connection = duckdb.connect(str(args.database), read_only=True)
    try:
        table_map = {
            "components": "metals_forecast_model_component_current",
            "regimes": "metals_regime_probability_current",
            "adjusted": "metals_uncertainty_adjusted_view_current",
            "changes": "metals_recommendation_change_current",
            "freshness": "metals_data_freshness_current",
            "health": "metals_platform_health_current",
        }

        observed_counts = {name: count_rows(connection, table) for name, table in table_map.items()}
        if observed_counts != EXPECTED_COUNTS:
            raise RuntimeError(f"Unexpected production Metals tactical evidence counts: {observed_counts}")

        lineage = {name: distinct_lineage(connection, table) for name, table in table_map.items()}
        for name, item in lineage.items():
            if item["package_ids"] != [EXPECTED_PACKAGE_ID]:
                raise RuntimeError(f"Unexpected package lineage for {name}: {item['package_ids']}")
            if item["import_ids"] != [EXPECTED_IMPORT_ID]:
                raise RuntimeError(f"Unexpected import lineage for {name}: {item['import_ids']}")
            if item["manifest_sha256"] != [EXPECTED_MANIFEST_SHA256]:
                raise RuntimeError(f"Unexpected manifest lineage for {name}: {item['manifest_sha256']}")

        component_sums = connection.execute(
            """
            SELECT universal_asset_id, horizon_months, SUM(model_weight)
            FROM metals_forecast_model_component_current
            GROUP BY 1, 2
            ORDER BY 1, 2
            """
        ).fetchall()
        if not component_sums or any(not math.isclose(float(row[2]), 1.0, abs_tol=1e-10) for row in component_sums):
            raise RuntimeError("Production component weights do not reconcile to one by asset/horizon.")

        regime_sums = connection.execute(
            """
            SELECT universal_asset_id, SUM(probability)
            FROM metals_regime_probability_current
            GROUP BY 1
            ORDER BY 1
            """
        ).fetchall()
        if not regime_sums or any(not math.isclose(float(row[1]), 1.0, abs_tol=1e-10) for row in regime_sums):
            raise RuntimeError("Production regime probabilities do not reconcile to one by asset.")

        adjusted_rows = connection.execute(
            """
            SELECT raw_expected_return, uncertainty_penalty, downside_penalty, adjusted_expected_return
            FROM metals_uncertainty_adjusted_view_current
            """
        ).fetchall()
        if not adjusted_rows:
            raise RuntimeError("No production uncertainty-adjusted Metals rows found.")
        for raw, uncertainty, downside, adjusted in adjusted_rows:
            expected = float(raw) - float(uncertainty) - float(downside)
            if not math.isclose(expected, float(adjusted), abs_tol=1e-10):
                raise RuntimeError("Production uncertainty-adjusted return arithmetic does not reconcile.")

        duplicate_checks = {
            "components": connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT universal_asset_id, horizon_months, model_name, COUNT(*) AS n
                    FROM metals_forecast_model_component_current
                    GROUP BY 1,2,3 HAVING n > 1
                )
                """
            ).fetchone()[0],
            "regimes": connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT universal_asset_id, regime, COUNT(*) AS n
                    FROM metals_regime_probability_current
                    GROUP BY 1,2 HAVING n > 1
                )
                """
            ).fetchone()[0],
            "adjusted": connection.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT universal_vehicle_id, horizon_months, COUNT(*) AS n
                    FROM metals_uncertainty_adjusted_view_current
                    GROUP BY 1,2 HAVING n > 1
                )
                """
            ).fetchone()[0],
        }
        if any(int(value) != 0 for value in duplicate_checks.values()):
            raise RuntimeError(f"Duplicate current Metals tactical evidence detected: {duplicate_checks}")

        automatic_execution = connection.execute(
            """
            SELECT automatic_execution_authorized
            FROM universal_domain_registry
            WHERE lower(domain_id)='metals'
            """
        ).fetchone()
        if automatic_execution is None or bool(automatic_execution[0]):
            raise RuntimeError("Metals automatic execution is unexpectedly authorized.")
    finally:
        connection.close()

    after = sha256_file(args.database)
    if after.lower() != expected_sha:
        raise RuntimeError("Database changed during read-only production verification.")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "database_sha256": after,
        "package_id": EXPECTED_PACKAGE_ID,
        "import_id": EXPECTED_IMPORT_ID,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "current_counts": observed_counts,
        "lineage": lineage,
        "component_weight_groups": len(component_sums),
        "regime_probability_groups": len(regime_sums),
        "adjusted_return_rows_reconciled": len(adjusted_rows),
        "duplicate_current_keys": duplicate_checks,
        "automatic_execution_authorized": False,
        "next_decision": "AUTHORIZE_METALS_PRESENTATION_CONTRACT_EXPANSION",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
