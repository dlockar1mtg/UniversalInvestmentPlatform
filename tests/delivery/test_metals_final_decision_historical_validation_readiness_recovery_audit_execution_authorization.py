from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config" / "metals" / "final_decision_historical_validation_readiness_recovery_audit_execution_authorization.json"


def load_auth() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_authorization_identity_and_source() -> None:
    data = load_auth()
    assert data["authorization_id"] == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-AUDIT-EXECUTION-AUTHORIZATION-1"
    assert data["source_design_id"] == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-DESIGN-1"
    assert data["source_design_head"] == "9c43488d3c9dea91df5b37380af1bdf61f290691"
    assert data["source_arbitration_audit_id"] == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-1"


def test_authorization_binds_certified_findings() -> None:
    findings = load_auth()["certified_arbitration_findings"]
    assert findings == {
        "integration_finding": "LEGITIMATE_SEPARATION",
        "pipeline_bypass_signal": False,
        "stale_authority_signal": False,
        "calibration_defect_proven": False,
        "adjusted_arithmetic_status": "PASS",
        "raw_adjusted_sign_conflict_count": 8,
        "historical_validation_ready": False,
    }


def test_required_execution_behavior_is_complete() -> None:
    behavior = load_auth()["required_execution_behavior"]
    assert len(behavior) == 18
    assert all(behavior.values())


def test_required_outputs_are_exact() -> None:
    outputs = load_auth()["required_outputs"]
    assert len(outputs) == 11
    assert all(outputs.values())


def test_readiness_taxonomy_is_bound() -> None:
    assert set(load_auth()["allowed_readiness_findings"]) == {
        "READY_FOR_BOUNDED_HISTORICAL_VALIDATION",
        "READY_AFTER_REALIZED_RETURN_DERIVATION",
        "READY_AFTER_HISTORY_JOIN_RECOVERY",
        "INSUFFICIENT_HISTORICAL_EVIDENCE",
        "BLOCKED_BY_CONSUMED_HOLDOUT_CONSTRAINT",
        "MULTIPLE_READINESS_GAPS",
        "UNRESOLVED",
    }


def test_only_read_only_recovery_and_local_evidence_are_authorized() -> None:
    boundary = load_auth()["authorization_boundary"]
    assert boundary["read_only_recovery_audit_execution_authorized"] is True
    assert boundary["local_evidence_artifact_write_authorized"] is True
    for key, value in boundary.items():
        if key in {
            "read_only_recovery_audit_execution_authorized",
            "local_evidence_artifact_write_authorized",
        }:
            continue
        assert value is False, key


def test_no_historical_validation_or_policy_activation_is_authorized() -> None:
    boundary = load_auth()["authorization_boundary"]
    assert boundary["historical_realized_return_derivation_authorized"] is False
    assert boundary["historical_validation_execution_authorized"] is False
    assert boundary["candidate_policy_backtest_authorized"] is False
    assert boundary["final_action_policy_authorized"] is False
    assert boundary["final_action_selection_authorized"] is False
    assert boundary["final_action_persistence_authorized"] is False


def test_authorization_and_next_decision_are_bound() -> None:
    data = load_auth()
    assert data["authorization_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_HISTORICAL_VALIDATION_READINESS_RECOVERY_AUDIT"
    assert data["next_decision"] == "EXECUTE_AND_CERTIFY_READ_ONLY_METALS_FINAL_DECISION_HISTORICAL_VALIDATION_READINESS_RECOVERY_AUDIT"
