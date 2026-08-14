from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.domain_registry import (
    DomainRegistryEntry,
    get_certified_domain,
    list_certified_domains,
)


def _config(tmp_path: Path) -> ImportEngineConfig:
    root = Path(__file__).resolve().parents[1]
    return ImportEngineConfig(
        repository_root=root,
        database_path=tmp_path / "uip.duckdb",
        schema_root=root / "schemas" / "v1" / "csv",
        integration_root=tmp_path / "integration",
        validation_root=tmp_path / "validation",
    )


def test_d1_fresh_database_contains_exactly_three_certified_domains(tmp_path):
    config = _config(tmp_path)
    initialize_database(config)

    with duckdb.connect(str(config.database_path), read_only=True) as con:
        domains = list_certified_domains(con)

    assert [entry.domain_id for entry in domains] == [
        "crypto",
        "metals",
        "mtg",
    ]
    assert all(entry.certification_state == "CERTIFIED" for entry in domains)
    assert all(entry.dynamic_asset_universe for entry in domains)
    assert all(entry.native_semantics_authoritative for entry in domains)
    assert not any(entry.cross_asset_ranking_authorized for entry in domains)
    assert not any(entry.automatic_execution_authorized for entry in domains)
    assert {entry.ownership_type for entry in domains} == {
        "external_source_repository",
        "uip_native_domain",
    }


def test_d1_registry_interface_has_no_permanent_asset_count_field():
    fields = set(DomainRegistryEntry.__dataclass_fields__)
    forbidden = {
        "asset_count",
        "population_count",
        "snapshot_count",
        "permanent_asset_count",
    }
    assert fields.isdisjoint(forbidden)


def test_d1_registry_lookup_fails_closed_for_unknown_domain(tmp_path):
    config = _config(tmp_path)
    initialize_database(config)

    with duckdb.connect(str(config.database_path), read_only=True) as con:
        assert get_certified_domain(con, "MTG").domain_id == "mtg"

        with pytest.raises(KeyError):
            get_certified_domain(con, "stocks")


def test_d1_lineage_views_exist_and_cover_certified_surfaces(tmp_path):
    config = _config(tmp_path)
    initialize_database(config)

    with duckdb.connect(str(config.database_path), read_only=True) as con:
        views = {
            row[0]
            for row in con.execute(
                """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'main'
                """
            ).fetchall()
        }

        lineage_columns = [
            row[0]
            for row in con.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'main'
                  AND table_name = 'universal_row_lineage'
                ORDER BY ordinal_position
                """
            ).fetchall()
        ]

    assert "universal_domain_operational_status" in views
    assert "universal_row_lineage" in views
    assert "universal_lineage_with_domain" in views
    assert lineage_columns == [
        "dataset_name",
        "platform_id",
        "universal_asset_id",
        "run_id",
        "_import_id",
        "_package_id",
        "_source_platform",
        "_source_filename",
        "_source_row_number",
        "_manifest_sha256",
        "_imported_at_utc",
    ]


def test_d1_lineage_preserves_mtg_native_authority_without_flattening(tmp_path):
    config = _config(tmp_path)
    initialize_database(config)

    with duckdb.connect(str(config.database_path)) as con:
        con.execute(
            """
            INSERT INTO mtg_native_authority_history (
                mtg_asset_id, mtg_lane, native_asset_id, product_name,
                lane_authority_state, current_price_usd,
                current_price_authority_available,
                forecast_authority_available, forecast_1y_price_usd,
                forecast_1y_return, risk_authority_available,
                native_rank, native_rank_type, native_purchase_status,
                purchase_semantic, evidence_state, actionability_state,
                execution_ready_purchase_certified,
                manual_execution_price_check_required,
                native_authority_pointer, native_authority_sha256,
                snapshot_population_is_permanent,
                automatic_purchase_execution,
                _import_id, _package_id, _source_platform,
                _source_filename, _source_row_number,
                _manifest_sha256, _imported_at_utc
            ) VALUES (
                'mtg:test', 'collector', 'test-native', 'Test',
                'CERTIFIED', NULL, FALSE, FALSE, NULL, NULL, FALSE,
                7, 'native_lane_rank', 'WAIT',
                'MODEL_NATIVE', 'CERTIFIED', 'WAIT', FALSE, TRUE,
                'authority.json', 'abc', FALSE, FALSE,
                'import-1', 'package-1', 'mtg',
                'mtg.csv', 1, 'manifest', CURRENT_TIMESTAMP
            )
            """
        )

        lineage = con.execute(
            """
            SELECT
                domain_id,
                dataset_name,
                universal_asset_id,
                _package_id,
                _source_platform
            FROM universal_lineage_with_domain
            WHERE dataset_name = 'mtg_native_authority'
            """
        ).fetchone()

        native = con.execute(
            """
            SELECT native_rank, native_rank_type, native_purchase_status
            FROM mtg_native_authority_current
            WHERE mtg_asset_id = 'mtg:test'
            """
        ).fetchone()

    assert lineage == (
        "mtg",
        "mtg_native_authority",
        "mtg:test",
        "package-1",
        "mtg",
    )
    assert native == (7, "native_lane_rank", "WAIT")
