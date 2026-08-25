from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "config" / "metals" / "tactical_policy_v3_production_persistence_authorization_design.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_production_persistence_authorization_design.py"


def load_design() -> dict:
    return json.loads(DESIGN.read_text(encoding="utf-8"))


def test_design_and_verifier_parse() -> None:
    load_design()
    ast.parse(VERIFIER.read_text(encoding="utf-8"))


def test_design_binds_certified_materialization() -> None:
    design = load_design()
    assert design["source_review_id"] == "METALS-TACTICAL-POLICY-V3-CURRENT-STATE-MATERIALIZATION-REVIEW-1"
    assert design["source_state_sha256"] == "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
    assert design["source_manifest_sha256"] == "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
    assert design["source_as_of_date"] == "2026-08-21"


def test_storage_is_append_only_history_plus_current_view() -> None:
    design = load_design()
    storage = design["target_storage_design"]
    assert storage["history_table"] == "metals_tactical_state_history"
    assert storage["current_view"] == "metals_tactical_state_current"
    assert storage["append_only"] is True
    assert storage["replace_existing_history_rows"] is False
    assert storage["delete_existing_history_rows"] is False
    assert storage["upsert_by_business_key"] is False
    assert storage["duplicate_exact_import_must_fail_closed"] is True
    assert storage["natural_business_key"] == [
        "universal_asset_id", "as_of_date", "classifier_rule_version", "action_mapping_version"
    ]


def test_universal_ingestion_metadata_is_required() -> None:
    required = set(load_design()["required_columns"])
    assert {
        "_import_id", "_package_id", "_source_platform", "_source_filename",
        "_source_row_number", "_manifest_sha256", "_imported_at_utc",
    }.issubset(required)


def test_tactical_specific_provenance_is_required() -> None:
    required = set(load_design()["required_columns"])
    assert "source_state_sha256" in required
    assert "source_materialization_manifest_sha256" in required
    provenance = load_design()["provenance_design"]
    assert provenance["source_state_sha256_required"] is True
    assert provenance["source_materialization_manifest_sha256_required"] is True
    assert provenance["source_row_number_must_match_jsonl_line_number"] is True
    assert provenance["all_11_rows_must_share_source_hashes"] is True


def test_transaction_is_atomic_and_fail_closed() -> None:
    txn = load_design()["write_transaction_design"]
    assert txn["single_duckdb_transaction_required"] is True
    assert txn["schema_and_view_creation_must_be_in_same_transaction_as_first_import"] is True
    assert txn["rollback_on_any_failure"] is True
    assert txn["postwrite_readback_must_match_source_rows"] is True
    assert txn["exact_source_row_count_required"] == 11
    assert txn["exact_opportunity_row_count_required"] == 10
    assert txn["exact_reference_control_row_count_required"] == 1


def test_semantic_guardrails_all_true() -> None:
    assert all(load_design()["semantic_guardrails"].values())


def test_fail_closed_controls_all_true() -> None:
    assert all(load_design()["fail_closed_design"].values())


def test_design_does_not_authorize_database_write_or_presentation() -> None:
    boundary = load_design()["authorization_boundary"]
    assert boundary["design_complete"] is True
    assert boundary["production_persistence_authorization_created"] is False
    assert boundary["schema_migration_authorized"] is False
    assert boundary["production_database_write_authorized"] is False
    assert boundary["production_database_write_executed"] is False
    assert boundary["presentation_activation_authorized"] is False
    assert boundary["network_collection_authorized"] is False
    assert boundary["model_retraining_authorized"] is False
    assert boundary["allocation_policy_authorized"] is False
    assert boundary["automatic_execution_authorized"] is False


def test_next_decision_is_authorization_consideration() -> None:
    assert load_design()["next_decision"] == "CONSIDER_METALS_TACTICAL_POLICY_V3_PRODUCTION_PERSISTENCE_AUTHORIZATION"
