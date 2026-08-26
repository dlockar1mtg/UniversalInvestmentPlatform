from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "metals" / "final_decision_arbitration_evidence_audit_execution_authorization.json"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_authorization_identity_and_bindings() -> None:
    data = load_config()
    assert data["authorization_id"] == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-EXECUTION-AUTHORIZATION-1"
    assert data["source_design_id"] == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-DESIGN-1"
    assert data["source_design_head"] == "86f785e2c1e4fe2d78949683c4c898fcce0d85c2"
    assert data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert data["active_hosted_publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert data["active_hosted_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
    assert data["active_hosted_record_count"] == 12477


def test_prior_conflict_runtime_authorization_is_superseded() -> None:
    superseded = load_config()["superseded_runtime_authorization"]
    assert superseded["authorization_id"] == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-IMPLEMENTATION-AUTHORIZATION-1"
    assert superseded["state"] == "SUPERSEDED_BY_FINAL_DECISION_REQUIREMENT"
    assert superseded["runtime_execution_allowed"] is False


def test_asset_scope_is_exact() -> None:
    expected = {
        "metals:commodity:gold",
        "metals:commodity:uranium",
        "metals:vehicle:BIL",
        "metals:vehicle:COPX",
        "metals:vehicle:CPER",
        "metals:vehicle:GLD",
        "metals:vehicle:IAU",
        "metals:vehicle:PPLT",
        "metals:vehicle:SGOL",
        "metals:vehicle:SIVR",
        "metals:vehicle:SLV",
        "metals:vehicle:URA",
    }
    assert set(load_config()["required_asset_scope"]) == expected


def test_execution_behavior_is_read_only_and_complete() -> None:
    behavior = load_config()["required_execution_behavior"]
    assert len(behavior) == 17
    assert all(value is True for value in behavior.values())
    assert behavior["no_final_action_may_be_selected_during_this_audit"] is True
    assert behavior["no_unvalidated_threshold_may_be_created"] is True


def test_integration_finding_taxonomy_is_bound() -> None:
    assert set(load_config()["allowed_integration_findings"]) == {
        "LEGITIMATE_SEPARATION",
        "PIPELINE_BYPASS",
        "STALE_AUTHORITY",
        "CALIBRATION_DEFECT",
        "MULTIPLE_CONTRIBUTING_CAUSES",
        "UNRESOLVED",
    }


def test_required_outputs_are_complete() -> None:
    outputs = load_config()["required_outputs"]
    assert len(outputs) == 11
    assert all(value is True for value in outputs.values())


def test_fail_closed_rules_are_complete() -> None:
    rules = load_config()["fail_closed_rules"]
    assert len(rules) == 13
    assert all(value is True for value in rules.values())


def test_only_read_only_audit_and_local_evidence_write_are_open() -> None:
    boundary = load_config()["authorization_boundary"]
    assert boundary["read_only_audit_execution_authorized"] is True
    assert boundary["local_evidence_artifact_write_authorized"] is True
    for key, value in boundary.items():
        if key in {"read_only_audit_execution_authorized", "local_evidence_artifact_write_authorized"}:
            continue
        assert value is False, key


def test_evidence_root_is_local_and_bounded() -> None:
    pattern = load_config()["authorized_evidence_root_pattern"]
    assert pattern == r"C:\Users\DevonLockard\UIP_Evidence\metals_final_decision_arbitration_audit_<YYYYMMDD>"


def test_authorization_decisions_are_exact() -> None:
    data = load_config()
    assert data["authorization_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_ARBITRATION_EVIDENCE_AUDIT"
    assert data["next_decision"] == "EXECUTE_AND_CERTIFY_READ_ONLY_METALS_FINAL_DECISION_ARBITRATION_EVIDENCE_AUDIT"
