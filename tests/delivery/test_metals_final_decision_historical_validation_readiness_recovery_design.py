from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "metals" / "final_decision_historical_validation_readiness_recovery_design.json"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_identity_and_source_bindings() -> None:
    data = load_config()
    assert data["design_id"] == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-DESIGN-1"
    assert data["source_governed_head"] == "b76cc6c219ec407b4c0eb386af386ae71fd1a502"
    assert data["source_arbitration_audit_id"] == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-1"
    assert data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_certified_arbitration_findings_are_bound() -> None:
    findings = load_config()["certified_arbitration_audit_findings"]
    assert findings == {
        "integration_finding": "LEGITIMATE_SEPARATION",
        "pipeline_bypass_signal": False,
        "stale_authority_signal": False,
        "calibration_defect_proven": False,
        "adjusted_arithmetic_status": "PASS",
        "raw_adjusted_sign_conflict_count": 8,
        "historical_validation_ready": False,
        "visible_adjusted_consumption": True,
        "final_action_selected": False,
        "new_threshold_created": False,
    }


def test_one_final_action_requirement_remains_bound() -> None:
    requirement = load_config()["final_decision_requirement"]
    assert len(requirement) == 7
    assert all(value is True for value in requirement.values())


def test_required_historical_evidence_classes_are_complete() -> None:
    evidence = load_config()["required_historical_evidence_classes"]
    assert len(evidence) == 10
    assert all(value is True for value in evidence.values())


def test_recovery_questions_are_complete() -> None:
    questions = load_config()["required_recovery_questions"]
    assert len(questions) == 16
    assert all(value is True for value in questions.values())


def test_validation_principles_are_complete() -> None:
    principles = load_config()["required_validation_principles"]
    assert len(principles) == 11
    assert all(value is True for value in principles.values())


def test_required_outputs_are_complete() -> None:
    outputs = load_config()["required_outputs"]
    assert len(outputs) == 11
    assert all(value is True for value in outputs.values())


def test_readiness_finding_taxonomy_is_bound() -> None:
    assert set(load_config()["allowed_readiness_findings"]) == {
        "READY_FOR_BOUNDED_HISTORICAL_VALIDATION",
        "READY_AFTER_REALIZED_RETURN_DERIVATION",
        "READY_AFTER_HISTORY_JOIN_RECOVERY",
        "INSUFFICIENT_HISTORICAL_EVIDENCE",
        "BLOCKED_BY_CONSUMED_HOLDOUT_CONSTRAINT",
        "MULTIPLE_READINESS_GAPS",
        "UNRESOLVED",
    }


def test_all_execution_boundaries_are_closed() -> None:
    boundaries = load_config()["boundaries"]
    assert all(value is False for value in boundaries.values())


def test_decision_and_next_decision_are_exact() -> None:
    data = load_config()
    assert data["design_decision"] == "APPROVE_METALS_FINAL_DECISION_HISTORICAL_VALIDATION_READINESS_RECOVERY_DESIGN_FOR_READ_ONLY_EXECUTION_AUTHORIZATION_CONSIDERATION"
    assert data["next_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_HISTORICAL_VALIDATION_READINESS_RECOVERY_AUDIT"
