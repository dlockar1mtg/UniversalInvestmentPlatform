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


def test_native_mtg_activation_suppresses_only_generic_current_authority(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "mtg-cutover.duckdb"
    initialize_database(_config(database_path))

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(
            """
            INSERT INTO asset_master_history (
                run_id, universal_asset_id, platform_asset_id, platform_id,
                asset_name, _import_id, _package_id, _source_platform,
                _source_filename, _source_row_number, _imported_at_utc,
                last_updated_at_utc
            ) VALUES
                ('legacy', 'MTG:SECRET_LAIR:SL-OLD', 'MTG:SECRET_LAIR:SL-OLD',
                 'MTG', 'Legacy Secret Lair', 'legacy-import', 'legacy-package',
                 'MTG', 'asset_master.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:20', TIMESTAMP '2026-07-28 18:23:19'),
                ('crypto', 'crypto:BTC', 'BTC', 'crypto', 'Bitcoin',
                 'crypto-import', 'crypto-package', 'crypto', 'asset_master.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:20', TIMESTAMP '2026-07-28 18:23:19')
            """
        )

        connection.execute(
            """
            INSERT INTO forecasts_history (
                run_id, universal_asset_id, platform_id, forecast_method,
                expected_return, _import_id, _package_id, _source_platform,
                _source_filename, _source_row_number, _imported_at_utc,
                generated_at_utc
            ) VALUES
                ('legacy', 'MTG:SECRET_LAIR:SL-OLD', 'MTG', 'LEGACY_METHOD',
                 0.25, 'legacy-import', 'legacy-package', 'MTG', 'forecasts.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:20', TIMESTAMP '2026-07-28 18:23:19')
            """
        )

        connection.execute(
            """
            INSERT INTO recommendations_history (
                run_id, universal_asset_id, platform_id, recommendation,
                _import_id, _package_id, _source_platform, _source_filename,
                _source_row_number, _imported_at_utc, generated_at_utc
            ) VALUES
                ('legacy', 'MTG:SECRET_LAIR:SL-OLD', 'MTG', 'WATCH',
                 'legacy-import', 'legacy-package', 'MTG', 'recommendations.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:20', TIMESTAMP '2026-07-28 18:23:19')
            """
        )

        connection.execute(
            """
            INSERT INTO risk_metrics_history (
                run_id, universal_asset_id, platform_id, _import_id, _package_id,
                _source_platform, _source_filename, _source_row_number,
                _imported_at_utc, generated_at_utc
            ) VALUES
                ('legacy', 'MTG:SECRET_LAIR:SL-OLD', 'MTG',
                 'legacy-import', 'legacy-package', 'MTG', 'risk_metrics.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:20', TIMESTAMP '2026-07-28 18:23:19')
            """
        )

        connection.execute(
            """
            INSERT INTO platform_status_history (
                run_id, platform_id, platform_name, adapter_version,
                contract_version, run_status, _import_id, _package_id,
                _source_platform, _source_filename, _source_row_number,
                _imported_at_utc, generated_at_utc
            ) VALUES
                ('legacy', 'MTG', 'MTG', 'legacy-adapter', 'v1', 'PASS',
                 'legacy-import', 'legacy-package', 'MTG', 'platform_status.csv', 1,
                 TIMESTAMP '2026-07-28 18:23:20', TIMESTAMP '2026-07-28 18:23:19')
            """
        )

        for table in (
            "asset_master_current",
            "forecasts_current",
            "recommendations_current",
            "risk_metrics_current",
        ):
            assert connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE lower(platform_id) = 'mtg'"
            ).fetchone()[0] == 1

        assert connection.execute(
            """
            SELECT platform_id, adapter_version
            FROM platform_status_current
            WHERE lower(platform_id) = 'mtg'
            """
        ).fetchall() == [('MTG', 'legacy-adapter')]

        connection.execute(
            """
            INSERT INTO mtg_native_authority_history (
                mtg_asset_id, mtg_lane, native_asset_id, product_name,
                lane_authority_state, current_price_usd,
                current_price_authority_available, forecast_authority_available,
                forecast_1y_price_usd, forecast_1y_return,
                risk_authority_available, native_rank, native_rank_type,
                native_purchase_status, purchase_semantic, evidence_state,
                actionability_state, execution_ready_purchase_certified,
                manual_execution_price_check_required, native_authority_pointer,
                native_authority_sha256, snapshot_population_is_permanent,
                automatic_purchase_execution, _import_id, _package_id,
                _source_platform, _source_filename, _source_row_number,
                _manifest_sha256, _imported_at_utc
            ) VALUES (
                'SECRET_LAIR_V1_1|SL-NEW', 'SECRET_LAIR_V1_1', 'SL-NEW',
                'Certified Secret Lair', 'CERTIFIED_CLOSED', 100.0, TRUE, TRUE,
                125.0, 0.25, TRUE, 1, 'SECRET_LAIR_NATIVE_RANK',
                'BUY_CANDIDATE_NOW', 'MODEL_QUALIFIED_ENTRY_CANDIDATE',
                'CERTIFIED', 'MODEL_QUALIFIED', FALSE, TRUE,
                'repository:authority.csv', 'abc123', FALSE, FALSE,
                'native-import', 'native-package', 'mtg',
                'mtg_native_authority.csv', 1, 'manifest-sha',
                TIMESTAMP '2026-08-21 22:30:00'
            )
            """
        )

        connection.execute(
            """
            INSERT INTO platform_status_history (
                run_id, platform_id, platform_name, adapter_version,
                contract_version, run_status, _import_id, _package_id,
                _source_platform, _source_filename, _source_row_number,
                _imported_at_utc, generated_at_utc
            ) VALUES
                ('native', 'mtg', 'MTG', 'mtg-v1-native-authority-binding-1.0.0',
                 '1.0.0', 'PASS', 'native-import', 'native-package', 'mtg',
                 'platform_status.csv', 1, TIMESTAMP '2026-08-21 22:30:00',
                 TIMESTAMP '2026-08-21 22:30:00')
            """
        )

        for table in (
            "asset_master_current",
            "forecasts_current",
            "recommendations_current",
            "risk_metrics_current",
        ):
            assert connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE lower(platform_id) = 'mtg'"
            ).fetchone()[0] == 0

        assert connection.execute(
            "SELECT COUNT(*) FROM mtg_native_authority_current"
        ).fetchone()[0] == 1

        assert connection.execute(
            "SELECT COUNT(*) FROM asset_master_history WHERE platform_id = 'MTG'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM forecasts_history WHERE platform_id = 'MTG'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM recommendations_history WHERE platform_id = 'MTG'"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM risk_metrics_history WHERE platform_id = 'MTG'"
        ).fetchone()[0] == 1

        assert connection.execute(
            """
            SELECT platform_id, adapter_version
            FROM platform_status_current
            WHERE lower(platform_id) = 'mtg'
            """
        ).fetchall() == [
            ('mtg', 'mtg-v1-native-authority-binding-1.0.0')
        ]

        assert connection.execute(
            "SELECT COUNT(*) FROM asset_master_current WHERE platform_id = 'crypto'"
        ).fetchone()[0] == 1
    finally:
        connection.close()
