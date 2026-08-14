from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from foundation.integrations.mtg.v1_export_acceptance import (
    MTGV1AcceptanceError,
    accept_mtg_v1_export,
)


FIELDS = [
    "mtg_asset_id",
    "mtg_lane",
    "native_asset_id",
    "product_name",
    "lane_authority_state",
    "current_price_usd",
    "current_price_authority_available",
    "forecast_authority_available",
    "forecast_1y_price_usd",
    "forecast_1y_return",
    "risk_authority_available",
    "native_rank",
    "native_rank_type",
    "native_purchase_status",
    "purchase_semantic",
    "evidence_state",
    "actionability_state",
    "execution_ready_purchase_certified",
    "manual_execution_price_check_required",
    "native_authority_pointer",
    "native_authority_sha256",
    "snapshot_population_is_permanent",
    "automatic_purchase_execution",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value),
        encoding="utf-8",
    )


def _fixture(root: Path) -> dict[str, Path]:
    payload = root / "payload.csv"

    rows = [
        {
            "mtg_asset_id": "COLLECTOR_V1|a",
            "mtg_lane": "COLLECTOR_V1",
            "native_asset_id": "a",
            "product_name": "Collector A",
            "lane_authority_state": "CERTIFIED_CLOSED",
            "current_price_usd": "100",
            "current_price_authority_available": "true",
            "forecast_authority_available": "true",
            "forecast_1y_price_usd": "110",
            "forecast_1y_return": "0.10",
            "risk_authority_available": "true",
            "native_rank": "",
            "native_rank_type": "",
            "native_purchase_status": "",
            "purchase_semantic": "",
            "evidence_state": "TEST",
            "actionability_state": "TEST",
            "execution_ready_purchase_certified": "false",
            "manual_execution_price_check_required": "true",
            "native_authority_pointer": "repository:test:a",
            "native_authority_sha256": "a" * 64,
            "snapshot_population_is_permanent": "false",
            "automatic_purchase_execution": "false",
        },
        {
            "mtg_asset_id": "PRE_COLLECTOR_V1|b",
            "mtg_lane": "PRE_COLLECTOR_V1",
            "native_asset_id": "b",
            "product_name": "Pre B",
            "lane_authority_state": "CERTIFIED_CLOSED",
            "current_price_usd": "",
            "current_price_authority_available": "false",
            "forecast_authority_available": "false",
            "forecast_1y_price_usd": "",
            "forecast_1y_return": "",
            "risk_authority_available": "true",
            "native_rank": "",
            "native_rank_type": "",
            "native_purchase_status": "",
            "purchase_semantic": "",
            "evidence_state": "TEST",
            "actionability_state": "TEST",
            "execution_ready_purchase_certified": "false",
            "manual_execution_price_check_required": "true",
            "native_authority_pointer": "repository:test:b",
            "native_authority_sha256": "b" * 64,
            "snapshot_population_is_permanent": "true",
            "automatic_purchase_execution": "false",
        },
        {
            "mtg_asset_id": "SECRET_LAIR_V1_1|c",
            "mtg_lane": "SECRET_LAIR_V1_1",
            "native_asset_id": "c",
            "product_name": "Secret C",
            "lane_authority_state": "CERTIFIED_CLOSED",
            "current_price_usd": "50",
            "current_price_authority_available": "true",
            "forecast_authority_available": "true",
            "forecast_1y_price_usd": "60",
            "forecast_1y_return": "0.20",
            "risk_authority_available": "true",
            "native_rank": "1",
            "native_rank_type": (
                "SECRET_LAIR_V1_1_PRODUCTION_COMPETITION_RANK"
            ),
            "native_purchase_status": "BUY_CANDIDATE_NOW",
            "purchase_semantic": (
                "MODEL_QUALIFIED_ENTRY_CANDIDATE"
            ),
            "evidence_state": "TEST",
            "actionability_state": (
                "MODEL_QUALIFIED_ENTRY_CANDIDATE"
            ),
            "execution_ready_purchase_certified": "false",
            "manual_execution_price_check_required": "true",
            "native_authority_pointer": "repository:test:c",
            "native_authority_sha256": "c" * 64,
            "snapshot_population_is_permanent": "false",
            "automatic_purchase_execution": "false",
        },
    ]

    with payload.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    canonical = _sha(payload)
    historical = "1" * 64
    blob = "2" * 40

    manifest = {
        "status": "MTG_V1_TO_UIP_EXPORT_PACKAGE_CERTIFIED",
        "payload_sha256": historical,
        "payload_repository_sha256": canonical,
        "source_and_payload_git_blob_sha1": blob,
        "repository_hash_verification_authorized": True,
        "payload_byte_identical_to_source": True,
        "payload_rows": 3,
        "payload_rows_are_permanent_universe_constant": False,
        "transformations_applied": 0,
        "execution_ready_purchase_certified": False,
        "automatic_purchase_execution": False,
        "UIP_integration_certified": False,
    }

    schema = {
        "status": "MTG_V1_UIP_EXPORT_SCHEMA_CERTIFIED",
        "source_schema_preserved_exactly": True,
        "field_count": len(FIELDS),
        "fields": [{"field": field} for field in FIELDS],
        "semantic_rules": {
            "native_rank_is_global_MTG_rank": False,
            "native_rank_is_cross_asset_UIP_rank": False,
            "native_purchase_status_is_universal_purchase_policy": False,
            "secret_lair_BUY_is_execution_ready": False,
            "missing_price_means_zero": False,
            "missing_forecast_means_zero": False,
            "missing_rank_means_worst_rank": False,
            "missing_purchase_status_means_WAIT": False,
            "current_snapshot_row_count_is_permanent_universe": False,
        },
    }

    permissions = [
        "INGEST_PAYLOAD",
        "STORE_PAYLOAD_WITH_LINEAGE",
        "DISPLAY_NATIVE_VALUES",
        "FILTER_BY_MTG_LANE",
        "FILTER_BY_NATIVE_PURCHASE_STATUS",
        "FILTER_BY_AUTHORITY_AVAILABILITY",
        "DISPLAY_NATIVE_RANK_WITH_NATIVE_RANK_TYPE",
        "DISPLAY_FORECAST_WHERE_AUTHORITY_AVAILABLE",
        "DISPLAY_EVIDENCE_AND_ACTIONABILITY_STATE",
        "ROUTE_RECORDS_TO_FUTURE_UIP_ANALYSIS_WITH_EXPLICIT_MTG_LINEAGE",
    ]

    prohibitions = [
        "REINTERPRET_NATIVE_RANK_AS_GLOBAL_MTG_RANK",
        "REINTERPRET_NATIVE_RANK_AS_CROSS_ASSET_UIP_RANK",
        "CREATE_CROSS_LANE_MTG_SCORE_WITHOUT_SEPARATE_GOVERNANCE",
        "TRANSFER_COLLECTOR_THRESHOLDS_TO_OTHER_LANES",
        "TRANSFER_PRECOLLECTOR_WEIGHTS_TO_OTHER_LANES",
        "TRANSFER_SECRET_LAIR_Q10_POLICY_TO_OTHER_LANES",
        "TREAT_SECRET_LAIR_BUY_AS_EXECUTION_READY",
        "REPLACE_MISSING_PRICE_WITH_ZERO",
        "REPLACE_MISSING_FORECAST_WITH_ZERO",
        "REPLACE_MISSING_RANK_WITH_WORST_RANK",
        "REPLACE_MISSING_PURCHASE_STATUS_WITH_WAIT",
        "TREAT_968_AS_PERMANENT_MTG_UNIVERSE",
        "TREAT_SECRET_LAIR_PRODUCT_COUNT_AS_FIXED",
        "AUTOMATIC_PURCHASE_EXECUTION",
    ]

    contract = {
        "status": "MTG_V1_TO_UIP_EXPORT_CONTRACT_CERTIFIED",
        "governed_source": {
            "production_authority_commit": "source-test-commit",
        },
        "payload": {
            "sha256": historical,
            "repository_sha256": canonical,
            "git_blob_sha1": blob,
            "repository_hash_verification_authorized": True,
            "byte_identical_to_certified_source_authority": True,
            "rows": 3,
            "row_count_is_permanent_universe_constant": False,
            "transformations_applied": 0,
            "rows_filtered": 0,
            "rows_added": 0,
            "rows_removed": 0,
            "columns_renamed": 0,
            "columns_reordered": 0,
            "missing_values_imputed": 0,
        },
        "current_snapshot": {
            "collector_rows": 1,
            "precollector_rows": 1,
            "secret_lair_rows": 1,
            "total_rows": 3,
            "secret_lair_dynamic_universe": True,
            "total_snapshot_is_permanent_universe": False,
        },
        "UIP_permitted_operations": permissions,
        "UIP_prohibited_operations": prohibitions,
        "secret_lair_execution_semantics": {
            "BUY_CANDIDATE_NOW": (
                "MODEL_QUALIFIED_ENTRY_CANDIDATE"
            ),
            "BUY_is_execution_ready": False,
            "manual_execution_price_check_required": True,
            "automatic_purchase_execution": False,
        },
        "authorization": {
            "UIP_acceptance_testing_authorized": True,
            "UIP_integration_certified": False,
            "UIP_cross_asset_ranking_authorized": False,
            "automatic_purchase_execution": False,
        },
        "hash_portability_correction": {
            "status": (
                "MTG_V1_TO_UIP_HASH_PORTABILITY_CORRECTION_CERTIFIED"
            ),
            "difference_scope": "LINE_ENDINGS_ONLY",
            "payload_content_changed": False,
            "model_semantics_changed": False,
        },
    }

    correction = {
        "status": (
            "MTG_V1_TO_UIP_HASH_PORTABILITY_CORRECTION_CERTIFIED"
        ),
        "git_object_identity": {
            "source_and_payload_same_git_blob": True,
            "git_blob_sha1": blob,
        },
        "hash_representations": {
            "historical_windows_crlf_sha256": historical,
            "canonical_repository_lf_sha256": canonical,
        },
        "data_integrity": {
            "payload_regenerated": False,
            "payload_rows_changed": 0,
            "payload_columns_changed": 0,
            "payload_values_changed": 0,
            "rows_filtered": 0,
            "rows_added": 0,
            "rows_removed": 0,
            "columns_renamed": 0,
            "columns_reordered": 0,
            "missing_values_imputed": 0,
        },
        "semantic_integrity": {
            "MTG_model_reopened": False,
            "MTG_lane_semantics_changed": False,
            "native_ranks_changed": False,
            "native_purchase_semantics_changed": False,
            "execution_authority_changed": False,
            "automatic_purchase_execution": False,
            "UIP_cross_asset_ranking_authorized": False,
        },
        "UIP_verification_authority": {
            "UIP_may_validate_canonical_repository_sha256": True,
            "UIP_must_not_silently_accept_arbitrary_hashes": True,
        },
    }

    paths = {
        "payload": payload,
        "manifest": root / "manifest.json",
        "schema": root / "schema.json",
        "contract": root / "contract.json",
        "portability": root / "portability.json",
    }

    _write_json(paths["manifest"], manifest)
    _write_json(paths["schema"], schema)
    _write_json(paths["contract"], contract)
    _write_json(paths["portability"], correction)

    return paths


def _accept(paths: dict[str, Path]):
    return accept_mtg_v1_export(
        payload_path=paths["payload"],
        manifest_path=paths["manifest"],
        schema_contract_path=paths["schema"],
        export_contract_path=paths["contract"],
        portability_correction_path=paths["portability"],
    )


def test_acceptance_is_snapshot_dynamic(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    result = _accept(paths)

    assert result.payload_rows == 3
    assert result.snapshot_population_is_permanent is False


def test_missing_values_are_preserved(tmp_path: Path) -> None:
    result = _accept(_fixture(tmp_path))

    assert result.blank_value_counts["current_price_usd"] == 1
    assert result.blank_value_counts["forecast_1y_price_usd"] == 1
    assert result.blank_value_counts["native_rank"] == 2
    assert result.blank_value_counts["native_purchase_status"] == 2


def test_rejects_arbitrary_payload_hash(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)

    with paths["payload"].open("ab") as handle:
        handle.write(b"\n")

    with pytest.raises(
        MTGV1AcceptanceError,
        match="canonical repository SHA",
    ):
        _accept(paths)


def test_rejects_duplicate_asset_ids(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)

    with paths["payload"].open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    rows[1]["mtg_asset_id"] = rows[0]["mtg_asset_id"]

    with paths["payload"].open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    new_sha = _sha(paths["payload"])

    manifest = json.loads(paths["manifest"].read_text())
    contract = json.loads(paths["contract"].read_text())
    portability = json.loads(paths["portability"].read_text())

    manifest["payload_repository_sha256"] = new_sha
    contract["payload"]["repository_sha256"] = new_sha
    portability["hash_representations"][
        "canonical_repository_lf_sha256"
    ] = new_sha

    _write_json(paths["manifest"], manifest)
    _write_json(paths["contract"], contract)
    _write_json(paths["portability"], portability)

    with pytest.raises(
        MTGV1AcceptanceError,
        match="duplicate governed MTG asset IDs",
    ):
        _accept(paths)


def test_rejects_secret_lair_buy_reinterpretation(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)

    with paths["payload"].open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    rows[2]["purchase_semantic"] = "EXECUTION_READY"

    with paths["payload"].open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    new_sha = _sha(paths["payload"])

    manifest = json.loads(paths["manifest"].read_text())
    contract = json.loads(paths["contract"].read_text())
    portability = json.loads(paths["portability"].read_text())

    manifest["payload_repository_sha256"] = new_sha
    contract["payload"]["repository_sha256"] = new_sha
    portability["hash_representations"][
        "canonical_repository_lf_sha256"
    ] = new_sha

    _write_json(paths["manifest"], manifest)
    _write_json(paths["contract"], contract)
    _write_json(paths["portability"], portability)

    with pytest.raises(
        MTGV1AcceptanceError,
        match="BUY semantic was reinterpreted",
    ):
        _accept(paths)


def test_rejects_automatic_execution(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)

    correction = json.loads(
        paths["portability"].read_text()
    )

    correction["semantic_integrity"][
        "automatic_purchase_execution"
    ] = True

    _write_json(paths["portability"], correction)

    with pytest.raises(
        MTGV1AcceptanceError,
        match="automatic_purchase_execution",
    ):
        _accept(paths)


def test_rejects_global_rank_authorization(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)

    contract = json.loads(
        paths["contract"].read_text()
    )

    contract["authorization"][
        "UIP_cross_asset_ranking_authorized"
    ] = True

    _write_json(paths["contract"], contract)

    with pytest.raises(
        MTGV1AcceptanceError,
        match="cross-asset ranking",
    ):
        _accept(paths)


def test_rejects_missing_value_imputation_authority(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)

    contract = json.loads(
        paths["contract"].read_text()
    )

    contract["payload"]["missing_values_imputed"] = 1

    _write_json(paths["contract"], contract)

    with pytest.raises(
        MTGV1AcceptanceError,
        match="missing_values_imputed",
    ):
        _accept(paths)

def test_cli_direct_invocation_can_import_repository_package() -> None:
    import subprocess
    import sys

    repository_root = Path(__file__).resolve().parents[1]
    cli = (
        repository_root
        / "scripts"
        / "validate_mtg_v1_export_acceptance.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(cli),
            "--help",
        ],
        cwd=repository_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--payload" in result.stdout
    assert "--portability" in result.stdout
