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


def test_metals_vehicle_case_transition_is_reconciled_only_in_current_views(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "identity.duckdb"
    initialize_database(_config(database_path))

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(
            """
            INSERT INTO asset_master_history (
                run_id,
                universal_asset_id,
                platform_asset_id,
                platform_id,
                asset_name,
                _import_id,
                _package_id,
                _source_platform,
                _source_filename,
                _source_row_number,
                _imported_at_utc,
                last_updated_at_utc
            ) VALUES
                ('old', 'metals:vehicle:gld', 'GLD', 'metals', 'GLD',
                 'old-import', 'old-package', 'metals', 'asset_master.csv', 1,
                 TIMESTAMP '2026-07-17 13:53:24', TIMESTAMP '2026-07-17 13:53:23'),
                ('new', 'metals:vehicle:GLD', 'GLD', 'metals', 'GLD',
                 'new-import', 'new-package', 'metals', 'asset_master.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:12', TIMESTAMP '2026-07-28 18:23:11'),
                ('crypto-old', 'crypto:Asset', 'Asset', 'crypto', 'Asset',
                 'crypto-old-import', 'crypto-old-package', 'crypto', 'asset_master.csv', 1,
                 TIMESTAMP '2026-07-17 13:53:24', TIMESTAMP '2026-07-17 13:53:23'),
                ('crypto-new', 'crypto:asset', 'asset', 'crypto', 'asset',
                 'crypto-new-import', 'crypto-new-package', 'crypto', 'asset_master.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:12', TIMESTAMP '2026-07-28 18:23:11')
            """
        )

        connection.execute(
            """
            INSERT INTO recommendations_history (
                run_id,
                universal_asset_id,
                platform_id,
                recommendation,
                _import_id,
                _package_id,
                _source_platform,
                _source_filename,
                _source_row_number,
                _imported_at_utc,
                generated_at_utc
            ) VALUES
                ('old', 'metals:vehicle:gld', 'metals', 'HOLD',
                 'old-import', 'old-package', 'metals', 'recommendations.csv', 1,
                 TIMESTAMP '2026-07-17 13:53:24', TIMESTAMP '2026-07-17 13:53:23'),
                ('new', 'metals:vehicle:GLD', 'metals', 'BUY',
                 'new-import', 'new-package', 'metals', 'recommendations.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:12', TIMESTAMP '2026-07-28 18:23:11')
            """
        )

        connection.execute(
            """
            INSERT INTO risk_metrics_history (
                run_id,
                universal_asset_id,
                platform_id,
                risk_score,
                _import_id,
                _package_id,
                _source_platform,
                _source_filename,
                _source_row_number,
                _imported_at_utc,
                generated_at_utc
            ) VALUES
                ('old', 'metals:vehicle:gld', 'metals', 20.0,
                 'old-import', 'old-package', 'metals', 'risk_metrics.csv', 1,
                 TIMESTAMP '2026-07-17 13:53:24', TIMESTAMP '2026-07-17 13:53:23'),
                ('new', 'metals:vehicle:GLD', 'metals', 10.0,
                 'new-import', 'new-package', 'metals', 'risk_metrics.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:12', TIMESTAMP '2026-07-28 18:23:11')
            """
        )

        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM asset_master_history
            WHERE platform_id = 'metals'
              AND lower(universal_asset_id) = 'metals:vehicle:gld'
            """
        ).fetchone()[0] == 2

        assert connection.execute(
            """
            SELECT universal_asset_id, _package_id
            FROM asset_master_current
            WHERE platform_id = 'metals'
              AND lower(universal_asset_id) = 'metals:vehicle:gld'
            """
        ).fetchall() == [('metals:vehicle:GLD', 'new-package')]

        assert connection.execute(
            """
            SELECT universal_asset_id, recommendation, _package_id
            FROM recommendations_current
            WHERE platform_id = 'metals'
              AND lower(universal_asset_id) = 'metals:vehicle:gld'
            """
        ).fetchall() == [('metals:vehicle:GLD', 'BUY', 'new-package')]

        assert connection.execute(
            """
            SELECT universal_asset_id, risk_score, _package_id
            FROM risk_metrics_current
            WHERE platform_id = 'metals'
              AND lower(universal_asset_id) = 'metals:vehicle:gld'
            """
        ).fetchall() == [('metals:vehicle:GLD', 10.0, 'new-package')]

        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM asset_master_current
            WHERE platform_id = 'crypto'
              AND lower(universal_asset_id) = 'crypto:asset'
            """
        ).fetchone()[0] == 2
    finally:
        connection.close()
