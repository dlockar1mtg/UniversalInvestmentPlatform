from __future__ import annotations

import csv
from pathlib import Path

import duckdb

import foundation.integrations.mtg.v1_integration_binding as binding
from foundation.integrations.mtg.r3_native_activation import (
    activate_mtg_v1_authority_for_r3,
)
from foundation.integrations.mtg.v1_export_acceptance import (
    MTGV1AcceptanceResult,
)


FIELDS = list(binding.NATIVE_FIELDS)


def _row(**overrides):
    base = {
        "mtg_asset_id": "mtg:collector:1",
        "mtg_lane": "COLLECTOR_V1",
        "native_asset_id": "collector-1",
        "product_name": "Collector Example",
        "lane_authority_state": "CERTIFIED",
        "current_price_usd": "100",
        "current_price_authority_available": "true",
        "forecast_authority_available": "true",
        "forecast_1y_price_usd": "120",
        "forecast_1y_return": "0.20",
        "risk_authority_available": "true",
        "native_rank": "1",
        "native_rank_type": "COLLECTOR_NATIVE_RANK",
        "native_purchase_status": "HOLD",
        "purchase_semantic": "NATIVE_HOLD",
        "evidence_state": "CERTIFIED",
        "actionability_state": "ACTIONABLE",
        "execution_ready_purchase_certified": "false",
        "manual_execution_price_check_required": "false",
        "native_authority_pointer": "authority/collector.csv",
        "native_authority_sha256": "a" * 64,
        "snapshot_population_is_permanent": "false",
        "automatic_purchase_execution": "false",
    }
    base.update(overrides)
    return base


def _payload(tmp_path: Path) -> Path:
    path = tmp_path / "payload.csv"
    rows = [
        _row(),
        _row(
            mtg_asset_id="mtg:precollector:1",
            mtg_lane="PRE_COLLECTOR_V1",
            native_asset_id="precollector-1",
            product_name="Pre Collector Example",
            current_price_usd="",
            current_price_authority_available="false",
            forecast_authority_available="false",
            forecast_1y_price_usd="",
            forecast_1y_return="",
            risk_authority_available="false",
            native_rank="",
            native_rank_type="",
            native_purchase_status="",
            purchase_semantic="",
            snapshot_population_is_permanent="true",
        ),
        _row(
            mtg_asset_id="mtg:secretlair:1",
            mtg_lane="SECRET_LAIR_V1_1",
            native_asset_id="secretlair-1",
            product_name="Secret Lair Example",
            native_rank="7",
            native_rank_type="SECRET_LAIR_NATIVE_RANK",
            native_purchase_status="BUY_CANDIDATE_NOW",
            purchase_semantic="MODEL_QUALIFIED_ENTRY_CANDIDATE",
            manual_execution_price_check_required="true",
        ),
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return path


def _acceptance(payload_path: Path) -> MTGV1AcceptanceResult:
    import hashlib

    blank_counts = {field: 0 for field in FIELDS}
    blank_counts.update(
        {
            "current_price_usd": 1,
            "forecast_1y_price_usd": 1,
            "forecast_1y_return": 1,
            "native_rank": 1,
            "native_rank_type": 1,
            "native_purchase_status": 1,
            "purchase_semantic": 1,
        }
    )

    return MTGV1AcceptanceResult(
        status="UIP_MTG_A1_EXPORT_ACCEPTANCE_PASS",
        payload_sha256=hashlib.sha256(payload_path.read_bytes()).hexdigest(),
        historical_windows_crlf_sha256="b" * 64,
        source_and_payload_git_blob_sha1="c" * 40,
        source_production_authority_commit="d" * 40,
        payload_rows=3,
        snapshot_population_is_permanent=False,
        field_count=23,
        lane_counts={
            "COLLECTOR_V1": 1,
            "PRE_COLLECTOR_V1": 1,
            "SECRET_LAIR_V1_1": 1,
        },
        blank_value_counts=blank_counts,
        duplicate_mtg_asset_ids=0,
        secret_lair_buy_candidate_rows=1,
        transformations_applied=0,
        rows_filtered=0,
        rows_added=0,
        rows_removed=0,
        columns_renamed=0,
        columns_reordered=0,
        missing_values_imputed=0,
        execution_ready_purchase_certified=False,
        automatic_purchase_execution=False,
        cross_asset_ranking_authorized=False,
        uip_integration_certified=False,
        generated_at_utc="2026-08-14T00:00:00+00:00",
    )


def test_r3_activation_imports_native_status_and_suppresses_legacy_current(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = _payload(tmp_path)
    acceptance = _acceptance(payload)

    monkeypatch.setattr(
        binding,
        "accept_mtg_v1_export",
        lambda **kwargs: acceptance,
    )

    repository_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "uip.duckdb"

    # Initialize first, then seed one recovery-era generic MTG row/status.
    from foundation.import_engine.config import ImportEngineConfig
    from foundation.import_engine.database import initialize_database

    base = ImportEngineConfig.from_repository_root(repository_root)
    config = ImportEngineConfig(
        repository_root=repository_root,
        database_path=database_path,
        schema_root=base.schema_root,
        integration_root=base.integration_root,
        validation_root=base.validation_root,
    )
    initialize_database(config)

    con = duckdb.connect(str(database_path))
    try:
        con.execute(
            """
            INSERT INTO asset_master_history (
                run_id, universal_asset_id, platform_asset_id, platform_id,
                asset_name, _import_id, _package_id, _source_platform,
                _source_filename, _source_row_number, _imported_at_utc,
                last_updated_at_utc
            ) VALUES (
                'legacy', 'MTG:SECRET_LAIR:OLD', 'MTG:SECRET_LAIR:OLD', 'MTG',
                'Legacy', 'legacy-import', 'legacy-package', 'MTG',
                'asset_master.csv', 1, TIMESTAMP '2026-07-28 18:23:20',
                TIMESTAMP '2026-07-28 18:23:19'
            )
            """
        )
        con.execute(
            """
            INSERT INTO platform_status_history (
                run_id, platform_id, platform_name, adapter_version,
                contract_version, run_status, _import_id, _package_id,
                _source_platform, _source_filename, _source_row_number,
                _imported_at_utc, generated_at_utc
            ) VALUES (
                'legacy', 'MTG', 'MTG', 'legacy-adapter', 'v1', 'PASS',
                'legacy-import', 'legacy-package', 'MTG', 'platform_status.csv', 1,
                TIMESTAMP '2026-07-28 18:23:20', TIMESTAMP '2026-07-28 18:23:19'
            )
            """
        )
    finally:
        con.close()

    result = activate_mtg_v1_authority_for_r3(
        repository_root=repository_root,
        payload_path=payload,
        manifest_path=tmp_path / "manifest.json",
        schema_contract_path=tmp_path / "schema.json",
        export_contract_path=tmp_path / "contract.json",
        portability_correction_path=tmp_path / "portability.json",
        database_path=database_path,
        workspace_root=tmp_path / "workspace",
        validation_root=tmp_path / "validation",
    )

    assert result.status == "UIP_R3_MTG_NATIVE_AUTHORITY_ACTIVATION_PASS"
    assert result.native_payload_rows == 3
    assert result.package_imported_row_count == 4
    assert result.native_history_row_count == 3
    assert result.native_current_row_count == 3
    assert result.platform_status_history_row_count == 1
    assert result.platform_status_current_row_count == 1
    assert result.platform_status_current_platform_id == "mtg"
    assert result.platform_status_current_adapter_version == (
        "mtg-v1-native-authority-binding-1.0.0"
    )
    assert result.generic_asset_current_rows == 0
    assert result.generic_forecast_current_rows == 0
    assert result.generic_recommendation_current_rows == 0
    assert result.generic_risk_current_rows == 0
    assert result.lineage_missing_rows == 0
    assert result.activation_certified is True

    con = duckdb.connect(str(database_path), read_only=True)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM asset_master_history WHERE platform_id='MTG'"
        ).fetchone()[0] == 1
        assert con.execute(
            "SELECT COUNT(*) FROM asset_master_current WHERE lower(platform_id)='mtg'"
        ).fetchone()[0] == 0
        assert con.execute(
            """
            SELECT platform_id, adapter_version
            FROM platform_status_current
            WHERE lower(platform_id)='mtg'
            """
        ).fetchall() == [
            ("mtg", "mtg-v1-native-authority-binding-1.0.0")
        ]
    finally:
        con.close()
