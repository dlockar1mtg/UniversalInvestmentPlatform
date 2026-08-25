from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_one_bounded_production_database_write_authorization.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_one_bounded_production_database_write_authorization.py"
IMPORTER_PATH = ROOT / "scripts" / "persist_metals_tactical_policy_v3_current_state.py"


def load_auth() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_identity_and_scope() -> None:
    auth = load_auth()
    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-ONE-BOUNDED-PRODUCTION-DATABASE-WRITE-AUTHORIZATION-1"
    assert auth["source_implementation_id"] == "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-IMPLEMENTATION-1"
    assert auth["source_implementation_head"] == "d64d2b3d3d948d61a3a3525bef3e4bd682720ad6"
    assert auth["authorization_decision"] == "AUTHORIZE_ONE_BOUNDED_METALS_V3_PRODUCTION_DATABASE_WRITE"
    assert auth["production_database_write_authorized"] is True
    assert auth["execution_limit"] == 1
    assert auth["execution_is_one_time"] is True


def test_exact_artifact_and_database_bindings() -> None:
    auth = load_auth()
    assert auth["required_prewrite_database_sha256"] == "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"
    assert auth["exact_state_sha256"] == "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
    assert auth["exact_manifest_sha256"] == "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
    assert auth["exact_as_of_date"] == "2026-08-21"
    assert auth["exact_row_count"] == 11
    assert auth["exact_opportunity_row_count"] == 10
    assert auth["exact_reference_control_row_count"] == 1


def test_storage_and_execution_controls() -> None:
    auth = load_auth()
    assert auth["history_table"] == "metals_tactical_state_history"
    assert auth["current_view"] == "metals_tactical_state_current"
    assert all(value is True for value in auth["required_execution_controls"].values())
    assert auth["required_execution_controls"]["second_execution_forbidden"] is True
    assert auth["required_execution_controls"]["duplicate_exact_import_must_fail_closed"] is True


def test_semantic_and_downstream_boundaries() -> None:
    auth = load_auth()
    assert all(value is True for value in auth["semantic_guardrails"].values())
    assert all(value is False for value in auth["downstream_authorization_boundary"].values())
    assert auth["downstream_authorization_boundary"]["presentation_activation_authorized"] is False
    assert auth["downstream_authorization_boundary"]["automatic_execution_authorized"] is False


def test_next_decision_is_exactly_one_bounded_execution() -> None:
    auth = load_auth()
    assert auth["next_decision"] == "EXECUTE_ONE_BOUNDED_METALS_TACTICAL_POLICY_V3_PRODUCTION_DATABASE_WRITE"


def test_verifier_is_read_only_and_binds_exact_authority() -> None:
    text = VERIFIER_PATH.read_text(encoding="utf-8")
    assert '"read_only": True' in text
    assert "METALS-TACTICAL-POLICY-V3-ONE-BOUNDED-PRODUCTION-DATABASE-WRITE-AUTHORIZATION-1" in text
    assert "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c" in text
    assert "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a" in text
    assert "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75" in text
    lowered = text.lower()
    assert "duckdb.connect" not in lowered
    assert "insert into" not in lowered
    assert "delete from" not in lowered
    assert "update metals_tactical_state_history" not in lowered


def test_certified_importer_accepts_separate_write_authorization_gate() -> None:
    text = IMPORTER_PATH.read_text(encoding="utf-8")
    assert "--production-write-authorization" in text
    assert 'write_auth.get("production_database_write_authorized") is not True' in text
    assert 'write_auth.get("exact_state_sha256") != EXPECTED_STATE_SHA' in text
    assert 'write_auth.get("exact_manifest_sha256") != EXPECTED_MANIFEST_SHA' in text
    assert "duplicate exact tactical-state import already exists" in text
