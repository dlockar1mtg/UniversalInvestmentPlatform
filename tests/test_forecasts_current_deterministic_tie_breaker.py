from __future__ import annotations

from pathlib import Path

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database


ROOT = Path(__file__).resolve().parents[1]


def _config(database_path: Path) -> ImportEngineConfig:
    base = ImportEngineConfig.from_repository_root(ROOT)
    return ImportEngineConfig(
        repository_root=ROOT,
        database_path=database_path,
        schema_root=base.schema_root,
        integration_root=base.integration_root,
        validation_root=base.validation_root,
    )


def test_forecasts_current_exact_timestamp_ties_use_stable_lineage_order(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "forecast-ties.duckdb"
    config = _config(database_path)
    initialize_database(config)

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(
            """
            INSERT INTO forecasts_history (
                run_id,
                universal_asset_id,
                platform_id,
                forecast_origin_date,
                forecast_horizon_months,
                forecast_method,
                point_forecast,
                expected_return,
                source_system,
                model_version,
                generated_at_utc,
                _import_id,
                _package_id,
                _source_platform,
                _source_filename,
                _source_row_number,
                _manifest_sha256,
                _imported_at_utc
            ) VALUES
                (
                    'run-1', 'crypto:bitcoin', 'crypto', DATE '2026-08-21',
                    1, 'CALIBRATED_ENSEMBLE', 100.0, 0.10,
                    'crypto', 'v1', TIMESTAMP '2026-08-21 12:00:00',
                    'same-import', 'same-package', 'crypto',
                    'forecasts.csv', 26, 'manifest',
                    TIMESTAMP '2026-08-21 12:00:01'
                ),
                (
                    'run-1', 'crypto:bitcoin', 'crypto', DATE '2026-08-21',
                    1, 'CALIBRATED_ENSEMBLE', 100.0, 0.10,
                    'crypto', 'v1', TIMESTAMP '2026-08-21 12:00:00',
                    'same-import', 'same-package', 'crypto',
                    'forecasts.csv', 24, 'manifest',
                    TIMESTAMP '2026-08-21 12:00:01'
                )
            """
        )
    finally:
        connection.close()

    # Reapply the full migration chain so the current view is rebuilt exactly as it
    # will be during production initialization.
    initialize_database(config)

    connection = duckdb.connect(str(database_path))
    try:
        first = connection.execute(
            """
            SELECT _source_row_number
            FROM forecasts_current
            WHERE platform_id = 'crypto'
              AND universal_asset_id = 'crypto:bitcoin'
              AND forecast_horizon_months = 1
              AND forecast_method = 'CALIBRATED_ENSEMBLE'
            """
        ).fetchall()
        assert first == [(24,)]
    finally:
        connection.close()

    # A second view rebuild must make the identical selection.
    initialize_database(config)

    connection = duckdb.connect(str(database_path))
    try:
        second = connection.execute(
            """
            SELECT _source_row_number
            FROM forecasts_current
            WHERE platform_id = 'crypto'
              AND universal_asset_id = 'crypto:bitcoin'
              AND forecast_horizon_months = 1
              AND forecast_method = 'CALIBRATED_ENSEMBLE'
            """
        ).fetchall()
        assert second == [(24,)]

        # The duplicate history rows remain immutable and preserved.
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM forecasts_history
            WHERE platform_id = 'crypto'
              AND universal_asset_id = 'crypto:bitcoin'
              AND forecast_horizon_months = 1
              AND forecast_method = 'CALIBRATED_ENSEMBLE'
            """
        ).fetchone()[0] == 2
    finally:
        connection.close()
