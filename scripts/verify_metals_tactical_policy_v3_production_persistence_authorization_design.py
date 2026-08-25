from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "config" / "metals" / "tactical_policy_v3_production_persistence_authorization_design.json"
REVIEW = ROOT / "config" / "metals" / "tactical_policy_v3_current_state_materialization_review.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))

    require(design["design_id"] == "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-AUTHORIZATION-DESIGN-1", "unexpected design id")
    require(design["source_review_id"] == review["review_id"], "source review id mismatch")
    require(design["source_review_decision"] == review["review_decision"], "source review decision mismatch")
    require(design["source_state_sha256"] == review["source_materialization_state_sha256"], "state hash mismatch")
    require(design["source_manifest_sha256"] == review["source_materialization_manifest_sha256"], "manifest hash mismatch")
    require(design["source_as_of_date"] == review["source_materialization_as_of_date"], "as-of date mismatch")

    db = design["database_standard"]
    require(db["database_path"] == "data/universal/universal_investment.duckdb", "database path changed")
    require(db["history_is_append_only"] is True, "history must be append only")
    require(db["current_state_is_view_derived"] is True, "current state must be view derived")
    require(db["ingestion_metadata_required"] is True, "ingestion metadata required")

    storage = design["target_storage_design"]
    require(storage["history_table"] == "metals_tactical_state_history", "history table changed")
    require(storage["current_view"] == "metals_tactical_state_current", "current view changed")
    require(storage["platform_id"] == "metals", "platform id changed")
    require(storage["natural_business_key"] == ["universal_asset_id", "as_of_date", "classifier_rule_version", "action_mapping_version"], "business key changed")
    require(storage["current_view_partition_key"] == ["universal_asset_id"], "current view partition changed")
    require(storage["append_only"] is True, "append-only storage required")
    require(storage["replace_existing_history_rows"] is False, "history replacement forbidden")
    require(storage["delete_existing_history_rows"] is False, "history deletion forbidden")
    require(storage["upsert_by_business_key"] is False, "upsert forbidden")
    require(storage["duplicate_exact_import_must_fail_closed"] is True, "duplicate import must fail closed")

    required_columns = set(design["required_columns"])
    for field in {
        "universal_asset_id", "ticker", "as_of_date", "candidate_regime", "tactical_state",
        "classifier_rule_version", "action_mapping_version", "price_semantics", "source_package_id",
        "state_available", "state_reason", "is_reference_control", "source_state_sha256",
        "source_materialization_manifest_sha256", "_import_id", "_package_id", "_source_platform",
        "_source_filename", "_source_row_number", "_manifest_sha256", "_imported_at_utc",
    }:
        require(field in required_columns, f"required column missing: {field}")

    txn = design["write_transaction_design"]
    for key in [
        "single_duckdb_transaction_required", "schema_and_view_creation_must_be_in_same_transaction_as_first_import",
        "prewrite_database_sha256_must_be_recorded", "postwrite_database_sha256_must_be_recorded",
        "source_artifact_hashes_must_be_reverified_before_write", "rollback_on_any_failure",
        "postwrite_readback_must_match_source_rows", "postwrite_current_view_must_return_exactly_11_metals_rows",
    ]:
        require(txn[key] is True, f"transaction control not true: {key}")
    require(txn["exact_source_row_count_required"] == 11, "source row count changed")
    require(txn["exact_opportunity_row_count_required"] == 10, "opportunity row count changed")
    require(txn["exact_reference_control_row_count_required"] == 1, "reference row count changed")

    for section in ["semantic_guardrails", "fail_closed_design"]:
        for key, value in design[section].items():
            require(value is True, f"{section} control not true: {key}")

    boundary = design["authorization_boundary"]
    require(boundary["design_complete"] is True, "design incomplete")
    for key, value in boundary.items():
        if key == "design_complete":
            continue
        require(value is False, f"downstream authority prematurely enabled: {key}")

    require(design["next_decision"] == "CONSIDER_METALS_TACTICAL_POLICY_V3_PRODUCTION_PERSISTENCE_AUTHORIZATION", "unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "design_id": design["design_id"],
        "history_table": storage["history_table"],
        "current_view": storage["current_view"],
        "database_path": db["database_path"],
        "append_only": storage["append_only"],
        "source_state_sha256": design["source_state_sha256"],
        "source_manifest_sha256": design["source_manifest_sha256"],
        "source_as_of_date": design["source_as_of_date"],
        "design_complete": boundary["design_complete"],
        "production_persistence_authorization_created": boundary["production_persistence_authorization_created"],
        "production_database_write_authorized": boundary["production_database_write_authorized"],
        "presentation_activation_authorized": boundary["presentation_activation_authorized"],
        "next_decision": design["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
