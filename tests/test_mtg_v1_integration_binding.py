from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

import foundation.integrations.mtg.v1_integration_binding as binding
from foundation.import_engine.exceptions import DuplicatePackageError
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
            snapshot_population_is_permanent="false",
        ),
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return path


def _acceptance(payload_path: Path) -> MTGV1AcceptanceResult:
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

    import hashlib

    return MTGV1AcceptanceResult(
        status="UIP_MTG_A1_EXPORT_ACCEPTANCE_PASS",
        payload_sha256=hashlib.sha256(
            payload_path.read_bytes()
        ).hexdigest(),
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


def _invoke(tmp_path: Path, monkeypatch):
    payload = _payload(tmp_path)
    acceptance = _acceptance(payload)

    monkeypatch.setattr(
        binding,
        "accept_mtg_v1_export",
        lambda **kwargs: acceptance,
    )

    repository_root = Path(__file__).resolve().parents[1]

    result = binding.import_mtg_v1_authority(
        repository_root=repository_root,
        payload_path=payload,
        manifest_path=tmp_path / "manifest.json",
        schema_contract_path=tmp_path / "schema.json",
        export_contract_path=tmp_path / "contract.json",
        portability_correction_path=tmp_path / "portability.json",
        database_path=tmp_path / "uip.duckdb",
        workspace_root=tmp_path / "workspace",
        validation_root=tmp_path / "validation",
    )

    return result, tmp_path / "uip.duckdb", payload


def test_a2_import_preserves_native_rows_and_lineage(
    tmp_path,
    monkeypatch,
):
    result, database_path, _ = _invoke(tmp_path, monkeypatch)

    assert result.status == "UIP_MTG_A2_INTEGRATION_CERTIFICATION_PASS"
    assert result.imported_row_count == 3
    assert result.history_row_count == 3
    assert result.current_row_count == 3
    assert result.field_count == 23
    assert result.duplicate_mtg_asset_ids == 0
    assert result.lineage_missing_rows == 0
    assert result.native_fields_preserved is True
    assert result.uip_integration_certified is True

    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        row = connection.execute(
            """
            SELECT
                mtg_lane,
                native_rank,
                native_rank_type,
                native_purchase_status,
                purchase_semantic,
                manual_execution_price_check_required,
                execution_ready_purchase_certified,
                automatic_purchase_execution
            FROM mtg_native_authority_current
            WHERE mtg_asset_id = 'mtg:secretlair:1'
            """
        ).fetchone()
    finally:
        connection.close()

    assert row == (
        "SECRET_LAIR_V1_1",
        7,
        "SECRET_LAIR_NATIVE_RANK",
        "BUY_CANDIDATE_NOW",
        "MODEL_QUALIFIED_ENTRY_CANDIDATE",
        True,
        False,
        False,
    )


def test_a2_missing_values_remain_database_null(
    tmp_path,
    monkeypatch,
):
    result, database_path, _ = _invoke(tmp_path, monkeypatch)

    assert result.null_value_counts["current_price_usd"] == 1
    assert result.null_value_counts["native_rank"] == 1
    assert result.null_value_counts["native_purchase_status"] == 1

    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        row = connection.execute(
            """
            SELECT
                current_price_usd,
                forecast_1y_price_usd,
                forecast_1y_return,
                native_rank,
                native_purchase_status
            FROM mtg_native_authority_current
            WHERE mtg_asset_id = 'mtg:precollector:1'
            """
        ).fetchone()
    finally:
        connection.close()

    assert row == (None, None, None, None, None)


def test_a2_creates_no_generic_semantic_outputs(
    tmp_path,
    monkeypatch,
):
    result, database_path, _ = _invoke(tmp_path, monkeypatch)

    assert result.cross_asset_rank_created is False
    assert result.generic_recommendation_created is False
    assert result.generic_forecast_created is False
    assert result.generic_risk_created is False
    assert result.execution_ready_true_rows == 0
    assert result.automatic_execution_true_rows == 0

    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        recommendation_count = connection.execute(
            "SELECT COUNT(*) FROM recommendations_history"
        ).fetchone()[0]
        forecast_count = connection.execute(
            "SELECT COUNT(*) FROM forecasts_history"
        ).fetchone()[0]
        risk_count = connection.execute(
            "SELECT COUNT(*) FROM risk_metrics_history"
        ).fetchone()[0]
    finally:
        connection.close()

    assert recommendation_count == 0
    assert forecast_count == 0
    assert risk_count == 0


def test_a2_package_id_is_deterministic(
    tmp_path,
    monkeypatch,
):
    payload = _payload(tmp_path)
    acceptance = _acceptance(payload)

    monkeypatch.setattr(
        binding,
        "accept_mtg_v1_export",
        lambda **kwargs: acceptance,
    )

    kwargs = dict(
        payload_path=payload,
        manifest_path=tmp_path / "manifest.json",
        schema_contract_path=tmp_path / "schema.json",
        export_contract_path=tmp_path / "contract.json",
        portability_correction_path=tmp_path / "portability.json",
    )

    first, _ = binding.build_mtg_v1_integration_package(
        workspace_root=tmp_path / "workspace1",
        **kwargs,
    )
    second, _ = binding.build_mtg_v1_integration_package(
        workspace_root=tmp_path / "workspace2",
        **kwargs,
    )

    assert first.name == second.name


def test_a2_duplicate_package_replay_is_rejected(
    tmp_path,
    monkeypatch,
):
    payload = _payload(tmp_path)
    acceptance = _acceptance(payload)

    monkeypatch.setattr(
        binding,
        "accept_mtg_v1_export",
        lambda **kwargs: acceptance,
    )

    repository_root = Path(__file__).resolve().parents[1]
    kwargs = dict(
        repository_root=repository_root,
        payload_path=payload,
        manifest_path=tmp_path / "manifest.json",
        schema_contract_path=tmp_path / "schema.json",
        export_contract_path=tmp_path / "contract.json",
        portability_correction_path=tmp_path / "portability.json",
        database_path=tmp_path / "uip.duckdb",
        workspace_root=tmp_path / "workspace",
        validation_root=tmp_path / "validation",
    )

    binding.import_mtg_v1_authority(**kwargs)

    with pytest.raises(DuplicatePackageError):
        binding.import_mtg_v1_authority(**kwargs)