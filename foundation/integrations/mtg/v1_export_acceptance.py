"""UIP-MTG-A1 certified export acceptance boundary.

Validation is evidence-driven. Snapshot population counts and payload hashes
are read from certified upstream authorities rather than encoded as permanent
UIP product-universe constants.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPORT_STATUS = "MTG_V1_TO_UIP_EXPORT_PACKAGE_CERTIFIED"
SCHEMA_STATUS = "MTG_V1_UIP_EXPORT_SCHEMA_CERTIFIED"
CONTRACT_STATUS = "MTG_V1_TO_UIP_EXPORT_CONTRACT_CERTIFIED"
PORTABILITY_STATUS = (
    "MTG_V1_TO_UIP_HASH_PORTABILITY_CORRECTION_CERTIFIED"
)

EXPECTED_LANES = {
    "COLLECTOR_V1": "collector_rows",
    "PRE_COLLECTOR_V1": "precollector_rows",
    "SECRET_LAIR_V1_1": "secret_lair_rows",
}

REQUIRED_PERMISSIONS = {
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
}

REQUIRED_PROHIBITIONS = {
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
}

REQUIRED_FALSE_SCHEMA_RULES = {
    "native_rank_is_global_MTG_rank",
    "native_rank_is_cross_asset_UIP_rank",
    "native_purchase_status_is_universal_purchase_policy",
    "secret_lair_BUY_is_execution_ready",
    "missing_price_means_zero",
    "missing_forecast_means_zero",
    "missing_rank_means_worst_rank",
    "missing_purchase_status_means_WAIT",
    "current_snapshot_row_count_is_permanent_universe",
}

BOOLEAN_FIELDS = (
    "current_price_authority_available",
    "forecast_authority_available",
    "risk_authority_available",
    "execution_ready_purchase_certified",
    "manual_execution_price_check_required",
    "snapshot_population_is_permanent",
    "automatic_purchase_execution",
)


class MTGV1AcceptanceError(RuntimeError):
    """Certified MTG V1 evidence failed UIP A1 acceptance."""


@dataclass(frozen=True)
class MTGV1AcceptanceResult:
    status: str
    payload_sha256: str
    historical_windows_crlf_sha256: str
    source_and_payload_git_blob_sha1: str
    source_production_authority_commit: str
    payload_rows: int
    snapshot_population_is_permanent: bool
    field_count: int
    lane_counts: dict[str, int]
    blank_value_counts: dict[str, int]
    duplicate_mtg_asset_ids: int
    secret_lair_buy_candidate_rows: int
    transformations_applied: int
    rows_filtered: int
    rows_added: int
    rows_removed: int
    columns_renamed: int
    columns_reordered: int
    missing_values_imputed: int
    execution_ready_purchase_certified: bool
    automatic_purchase_execution: bool
    cross_asset_ranking_authorized: bool
    uip_integration_certified: bool
    generated_at_utc: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MTGV1AcceptanceError(message)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MTGV1AcceptanceError(
            f"Unable to parse JSON authority: {path}"
        ) from exc

    if not isinstance(value, dict):
        raise MTGV1AcceptanceError(
            f"JSON authority must be an object: {path}"
        )

    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def _as_bool(value: object, label: str) -> bool:
    text = str(value).strip().lower()

    if text == "true":
        return True

    if text == "false":
        return False

    raise MTGV1AcceptanceError(
        f"{label} must be literal true or false; found {value!r}"
    )


def accept_mtg_v1_export(
    *,
    payload_path: Path,
    manifest_path: Path,
    schema_contract_path: Path,
    export_contract_path: Path,
    portability_correction_path: Path,
    report_path: Path | None = None,
) -> MTGV1AcceptanceResult:

    payload = payload_path.resolve()
    manifest = _load_json(manifest_path.resolve())
    schema = _load_json(schema_contract_path.resolve())
    contract = _load_json(export_contract_path.resolve())
    correction = _load_json(portability_correction_path.resolve())

    _require(
        manifest.get("status") == EXPORT_STATUS,
        "Export manifest is not certified.",
    )

    _require(
        schema.get("status") == SCHEMA_STATUS,
        "Schema contract is not certified.",
    )

    _require(
        contract.get("status") == CONTRACT_STATUS,
        "Export contract is not certified.",
    )

    _require(
        correction.get("status") == PORTABILITY_STATUS,
        "Hash-portability correction is not certified.",
    )

    hash_representations = correction.get(
        "hash_representations",
        {},
    )

    canonical_sha = str(
        hash_representations.get(
            "canonical_repository_lf_sha256",
            "",
        )
    ).lower()

    historical_sha = str(
        hash_representations.get(
            "historical_windows_crlf_sha256",
            "",
        )
    ).lower()

    _require(
        len(canonical_sha) == 64,
        "Canonical repository SHA authority is missing.",
    )

    _require(
        len(historical_sha) == 64,
        "Historical CRLF SHA authority is missing.",
    )

    actual_sha = _sha256(payload)

    _require(
        actual_sha == canonical_sha,
        "Payload does not match certified canonical repository SHA.",
    )

    verification = correction.get(
        "UIP_verification_authority",
        {},
    )

    _require(
        verification.get(
            "UIP_may_validate_canonical_repository_sha256"
        )
        is True,
        "UIP canonical repository verification is not authorized.",
    )

    _require(
        verification.get(
            "UIP_must_not_silently_accept_arbitrary_hashes"
        )
        is True,
        "Arbitrary hash substitution prohibition is missing.",
    )

    git_identity = correction.get(
        "git_object_identity",
        {},
    )

    git_blob = str(
        git_identity.get("git_blob_sha1", "")
    )

    _require(
        git_identity.get(
            "source_and_payload_same_git_blob"
        )
        is True,
        "Source and payload are not certified as the same Git blob.",
    )

    _require(
        len(git_blob) == 40,
        "Certified source/payload Git blob identity is missing.",
    )

    _require(
        manifest.get("payload_sha256") == historical_sha,
        "Manifest historical SHA does not reconcile.",
    )

    _require(
        manifest.get("payload_repository_sha256") == canonical_sha,
        "Manifest repository SHA does not reconcile.",
    )

    _require(
        manifest.get("source_and_payload_git_blob_sha1") == git_blob,
        "Manifest Git blob identity does not reconcile.",
    )

    _require(
        manifest.get("repository_hash_verification_authorized")
        is True,
        "Manifest does not authorize repository hash verification.",
    )

    _require(
        manifest.get("payload_byte_identical_to_source") is True,
        "Manifest does not certify byte identity to source authority.",
    )

    _require(
        manifest.get(
            "payload_rows_are_permanent_universe_constant"
        )
        is False,
        "Manifest incorrectly makes snapshot row count permanent.",
    )

    _require(
        int(manifest.get("transformations_applied", -1)) == 0,
        "Manifest reports transformations.",
    )

    _require(
        manifest.get("execution_ready_purchase_certified")
        is False,
        "Manifest exports execution-ready purchase authority.",
    )

    _require(
        manifest.get("automatic_purchase_execution")
        is False,
        "Manifest authorizes automatic purchase execution.",
    )

    _require(
        manifest.get("UIP_integration_certified")
        is False,
        "Manifest prematurely certifies UIP integration.",
    )

    payload_contract = contract.get("payload", {})

    _require(
        payload_contract.get("sha256") == historical_sha,
        "Contract historical SHA does not reconcile.",
    )

    _require(
        payload_contract.get("repository_sha256") == canonical_sha,
        "Contract repository SHA does not reconcile.",
    )

    _require(
        payload_contract.get("git_blob_sha1") == git_blob,
        "Contract Git blob identity does not reconcile.",
    )

    _require(
        payload_contract.get(
            "repository_hash_verification_authorized"
        )
        is True,
        "Contract repository hash verification is not authorized.",
    )

    _require(
        payload_contract.get(
            "byte_identical_to_certified_source_authority"
        )
        is True,
        "Contract does not preserve certified source byte identity.",
    )

    _require(
        payload_contract.get(
            "row_count_is_permanent_universe_constant"
        )
        is False,
        "Contract makes snapshot population permanent.",
    )

    zero_controls = (
        "transformations_applied",
        "rows_filtered",
        "rows_added",
        "rows_removed",
        "columns_renamed",
        "columns_reordered",
        "missing_values_imputed",
    )

    for key in zero_controls:
        _require(
            int(payload_contract.get(key, -1)) == 0,
            f"Contract reports nonzero {key}.",
        )

    portability_contract = contract.get(
        "hash_portability_correction",
        {},
    )

    _require(
        portability_contract.get("status") == PORTABILITY_STATUS,
        "Contract portability status is not certified.",
    )

    _require(
        portability_contract.get("difference_scope")
        == "LINE_ENDINGS_ONLY",
        "Hash portability difference is not line endings only.",
    )

    _require(
        portability_contract.get("payload_content_changed")
        is False,
        "Hash correction changed payload content.",
    )

    _require(
        portability_contract.get("model_semantics_changed")
        is False,
        "Hash correction changed model semantics.",
    )

    integrity = correction.get("data_integrity", {})

    for key in (
        "payload_rows_changed",
        "payload_columns_changed",
        "payload_values_changed",
        "rows_filtered",
        "rows_added",
        "rows_removed",
        "columns_renamed",
        "columns_reordered",
        "missing_values_imputed",
    ):
        _require(
            int(integrity.get(key, -1)) == 0,
            f"Portability authority reports nonzero {key}.",
        )

    _require(
        integrity.get("payload_regenerated") is False,
        "Portability correction regenerated payload.",
    )

    semantic_integrity = correction.get(
        "semantic_integrity",
        {},
    )

    for key in (
        "MTG_model_reopened",
        "MTG_lane_semantics_changed",
        "native_ranks_changed",
        "native_purchase_semantics_changed",
        "execution_authority_changed",
        "automatic_purchase_execution",
        "UIP_cross_asset_ranking_authorized",
    ):
        _require(
            semantic_integrity.get(key) is False,
            f"Portability semantic control changed: {key}.",
        )

    authorization = contract.get("authorization", {})

    _require(
        authorization.get(
            "UIP_acceptance_testing_authorized"
        )
        is True,
        "UIP A1 acceptance testing is not authorized.",
    )

    _require(
        authorization.get("UIP_integration_certified")
        is False,
        "Contract prematurely certifies UIP integration.",
    )

    _require(
        authorization.get(
            "UIP_cross_asset_ranking_authorized"
        )
        is False,
        "Contract authorizes cross-asset ranking.",
    )

    _require(
        authorization.get("automatic_purchase_execution")
        is False,
        "Contract authorizes automatic purchase execution.",
    )

    permissions = set(
        contract.get("UIP_permitted_operations", [])
    )

    prohibitions = set(
        contract.get("UIP_prohibited_operations", [])
    )

    _require(
        REQUIRED_PERMISSIONS.issubset(permissions),
        "Contract is missing required UIP permissions.",
    )

    _require(
        REQUIRED_PROHIBITIONS.issubset(prohibitions),
        "Contract is missing required UIP prohibitions.",
    )

    secret_lair = contract.get(
        "secret_lair_execution_semantics",
        {},
    )

    _require(
        secret_lair.get("BUY_CANDIDATE_NOW")
        == "MODEL_QUALIFIED_ENTRY_CANDIDATE",
        "Secret Lair BUY semantic changed.",
    )

    _require(
        secret_lair.get("BUY_is_execution_ready")
        is False,
        "Secret Lair BUY is incorrectly execution-ready.",
    )

    _require(
        secret_lair.get(
            "manual_execution_price_check_required"
        )
        is True,
        "Secret Lair BUY no longer requires manual price validation.",
    )

    _require(
        secret_lair.get("automatic_purchase_execution")
        is False,
        "Secret Lair automatic execution is authorized.",
    )

    _require(
        schema.get("source_schema_preserved_exactly")
        is True,
        "Schema is not preserved exactly.",
    )

    field_metadata = schema.get("fields")

    _require(
        isinstance(field_metadata, list),
        "Schema field metadata is missing.",
    )

    expected_fields = [
        str(item["field"])
        for item in field_metadata
        if isinstance(item, dict) and "field" in item
    ]

    _require(
        len(expected_fields)
        == int(schema.get("field_count", -1)),
        "Schema field count does not reconcile.",
    )

    semantic_rules = schema.get("semantic_rules", {})

    for rule in REQUIRED_FALSE_SCHEMA_RULES:
        _require(
            semantic_rules.get(rule) is False,
            f"Schema semantic rule changed: {rule}.",
        )

    with payload.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        _require(
            reader.fieldnames is not None,
            "Payload has no CSV header.",
        )

        actual_fields = list(reader.fieldnames)

        rows = [
            {
                str(key): "" if value is None else str(value)
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]

    _require(
        actual_fields == expected_fields,
        "Payload columns/order differ from certified schema.",
    )

    expected_rows = int(
        payload_contract.get("rows", -1)
    )

    _require(
        len(rows) == expected_rows,
        "Payload row count differs from certified contract.",
    )

    _require(
        len(rows) == int(manifest.get("payload_rows", -1)),
        "Payload row count differs from certified manifest.",
    )

    current_snapshot = contract.get(
        "current_snapshot",
        {},
    )

    _require(
        len(rows)
        == int(current_snapshot.get("total_rows", -1)),
        "Payload row count differs from snapshot evidence.",
    )

    _require(
        current_snapshot.get(
            "total_snapshot_is_permanent_universe"
        )
        is False,
        "Current MTG snapshot is incorrectly permanent.",
    )

    _require(
        current_snapshot.get("secret_lair_dynamic_universe")
        is True,
        "Secret Lair universe is not certified dynamic.",
    )

    ids = [
        row.get("mtg_asset_id", "")
        for row in rows
    ]

    _require(
        all(ids),
        "Payload contains blank governed MTG asset IDs.",
    )

    duplicate_count = len(ids) - len(set(ids))

    _require(
        duplicate_count == 0,
        "Payload contains duplicate governed MTG asset IDs.",
    )

    lane_counts = Counter(
        row.get("mtg_lane", "")
        for row in rows
    )

    _require(
        set(lane_counts) == set(EXPECTED_LANES),
        "Payload lane set differs from certified MTG lanes.",
    )

    for lane, snapshot_key in EXPECTED_LANES.items():
        _require(
            lane_counts[lane]
            == int(current_snapshot.get(snapshot_key, -1)),
            f"Lane count does not reconcile: {lane}.",
        )

    for row_number, row in enumerate(rows, start=2):
        for field in BOOLEAN_FIELDS:
            _as_bool(
                row.get(field, ""),
                f"row {row_number} {field}",
            )

        _require(
            row.get("native_authority_pointer", "") != "",
            f"Row {row_number} lacks native authority pointer.",
        )

        _require(
            row.get("native_authority_sha256", "") != "",
            f"Row {row_number} lacks native authority SHA.",
        )

        _require(
            _as_bool(
                row["execution_ready_purchase_certified"],
                "execution_ready_purchase_certified",
            )
            is False,
            f"Row {row_number} exports execution-ready authority.",
        )

        _require(
            _as_bool(
                row["automatic_purchase_execution"],
                "automatic_purchase_execution",
            )
            is False,
            f"Row {row_number} authorizes automatic execution.",
        )

        if row.get("mtg_lane") == "SECRET_LAIR_V1_1":
            _require(
                _as_bool(
                    row["snapshot_population_is_permanent"],
                    "Secret Lair snapshot_population_is_permanent",
                )
                is False,
                "Secret Lair population is incorrectly permanent.",
            )

            if (
                row.get("native_purchase_status")
                == "BUY_CANDIDATE_NOW"
            ):
                _require(
                    row.get("purchase_semantic")
                    == "MODEL_QUALIFIED_ENTRY_CANDIDATE",
                    "Secret Lair BUY semantic was reinterpreted.",
                )

                _require(
                    _as_bool(
                        row[
                            "manual_execution_price_check_required"
                        ],
                        "Secret Lair manual price validation",
                    )
                    is True,
                    "Secret Lair BUY lacks manual price validation.",
                )

    blank_counts = {
        field: sum(
            1
            for row in rows
            if row.get(field, "") == ""
        )
        for field in actual_fields
    }

    buy_count = sum(
        1
        for row in rows
        if (
            row.get("mtg_lane") == "SECRET_LAIR_V1_1"
            and row.get("native_purchase_status")
            == "BUY_CANDIDATE_NOW"
        )
    )

    source_commit = str(
        contract.get("governed_source", {}).get(
            "production_authority_commit",
            "",
        )
    )

    result = MTGV1AcceptanceResult(
        status="UIP_MTG_A1_EXPORT_ACCEPTANCE_PASS",
        payload_sha256=canonical_sha,
        historical_windows_crlf_sha256=historical_sha,
        source_and_payload_git_blob_sha1=git_blob,
        source_production_authority_commit=source_commit,
        payload_rows=len(rows),
        snapshot_population_is_permanent=False,
        field_count=len(actual_fields),
        lane_counts=dict(sorted(lane_counts.items())),
        blank_value_counts=blank_counts,
        duplicate_mtg_asset_ids=duplicate_count,
        secret_lair_buy_candidate_rows=buy_count,
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
        generated_at_utc=datetime.now(
            timezone.utc
        ).isoformat(),
    )

    if report_path is not None:
        destination = report_path.resolve()
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.write_text(
            json.dumps(
                asdict(result),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    return result
