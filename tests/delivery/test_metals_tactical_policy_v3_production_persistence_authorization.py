from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_production_persistence_authorization.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_production_persistence_authorization.py"


def load() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_authorization_identity_and_decision() -> None:
    auth = load()
    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-AUTHORIZATION-1"
    assert auth["source_design_id"] == "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-AUTHORIZATION-DESIGN-1"
    assert auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_V3_PRODUCTION_PERSISTENCE_IMPLEMENTATION"


def test_authorization_binds_exact_certified_materialization() -> None:
    auth = load()
    assert auth["source_state_sha256"] == "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
    assert auth["source_manifest_sha256"] == "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
    assert auth["source_as_of_date"] == "2026-08-21"
    scope = auth["authorized_source_scope"]
    assert scope["exact_row_count"] == 11
    assert scope["exact_opportunity_row_count"] == 10
    assert scope["exact_reference_control_row_count"] == 1
    assert scope["price_semantics"] == "UNADJUSTED_CLOSE"
    assert scope["classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert scope["action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1"


def test_authorization_locks_storage_contract() -> None:
    storage = load()["authorized_storage"]
    assert storage["database_path"] == "data/universal/universal_investment.duckdb"
    assert storage["history_table"] == "metals_tactical_state_history"
    assert storage["current_view"] == "metals_tactical_state_current"
    assert storage["history_is_append_only"] is True
    assert storage["current_state_is_view_derived"] is True
    assert storage["schema_migration_authorized"] is True
    assert storage["persistence_implementation_authorized"] is True
    assert storage["production_database_write_authorized"] is False
    assert storage["one_bounded_import_may_be_authorized_only_after_implementation_certification"] is True


def test_transaction_controls_all_fail_closed() -> None:
    controls = load()["required_transaction_controls"]
    assert controls
    assert all(controls.values())
    for key in [
        "single_duckdb_transaction_required",
        "source_hashes_reverified_before_write",
        "prewrite_database_sha256_recorded",
        "postwrite_database_sha256_recorded",
        "rollback_on_any_failure",
        "postwrite_readback_exact_match_required",
        "duplicate_exact_import_must_fail_closed",
        "history_replacement_forbidden",
        "history_deletion_forbidden",
        "business_key_upsert_forbidden",
    ]:
        assert controls[key] is True


def test_downstream_authorities_remain_off() -> None:
    boundary = load()["downstream_authorization_boundary"]
    assert boundary
    assert all(value is False for value in boundary.values())
    assert boundary["production_database_write_authorized"] is False
    assert boundary["presentation_activation_authorized"] is False
    assert boundary["network_collection_authorized"] is False
    assert boundary["model_retraining_authorized"] is False
    assert boundary["allocation_policy_authorized"] is False
    assert boundary["automatic_execution_authorized"] is False


def test_semantic_guardrails_preserved() -> None:
    guardrails = load()["semantic_guardrails"]
    assert guardrails
    assert all(guardrails.values())


def test_next_decision_is_implementation_only() -> None:
    assert load()["next_decision"] == "IMPLEMENT_METALS_TACTICAL_POLICY_V3_PRODUCTION_PERSISTENCE"


def test_verifier_is_read_only_and_does_not_import_duckdb() -> None:
    text = VERIFIER.read_text(encoding="utf-8")
    assert "import duckdb" not in text
    assert '"read_only": True' in text
