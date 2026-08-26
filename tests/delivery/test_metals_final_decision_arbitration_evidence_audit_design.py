from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "final_decision_arbitration_evidence_audit_design.json"


def load_design() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_design_identity_and_source_bindings() -> None:
    data = load_design()
    assert data["design_id"] == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-DESIGN-1"
    assert data["source_governed_head"] == "9a4f009cc7d4080b4ff142c8c67793bd31b51768"
    assert data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert data["source_semantic_audit_id"] == "METALS-DECISION-SEMANTICS-AUDIT-EXECUTION-1"


def test_prior_conflict_runtime_authorization_is_superseded() -> None:
    data = load_design()
    prior = data["superseded_runtime_authorization"]
    assert prior["authorization_id"] == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-IMPLEMENTATION-AUTHORIZATION-1"
    assert prior["state"] == "SUPERSEDED_BY_FINAL_DECISION_REQUIREMENT"
    assert prior["runtime_execution_allowed"] is False


def test_one_final_action_is_required() -> None:
    req = load_design()["final_decision_requirement"]
    assert req["one_final_uip_action_per_investable_asset"] is True
    assert req["internal_evidence_disagreement_may_be_preserved"] is True
    assert req["internal_conflict_must_not_be_final_action"] is True
    assert req["final_action_must_be_evidence_based"] is True
    assert req["final_action_must_be_explainable"] is True
    assert req["final_action_must_be_backtestable_before_production_activation"] is True
    assert req["final_action_must_not_be_invented_from_unvalidated_thresholds"] is True


def test_documented_pipeline_facts_are_bound() -> None:
    facts = load_design()["documented_pipeline_facts"]
    assert facts
    assert all(value is True for value in facts.values())
    assert facts["uncertainty_adjusted_views_precede_decision_support_in_native_data_flow"] is True
    assert facts["uncertainty_adjusted_views_are_documented_as_forecast_and_recommendation_evidence"] is True
    assert facts["phase_6_1_uses_12_month_raw_forecast_for_signal_mapping"] is True
    assert facts["uip_adapter_does_not_arbitrate_vehicle_action_against_uncertainty_adjusted_view"] is True


def test_audit_scope_and_questions_are_complete() -> None:
    data = load_design()
    assert len(data["required_asset_scope"]) == 12
    assert len(set(data["required_asset_scope"])) == 12
    questions = data["required_audit_questions"]
    assert len(questions) == 16
    assert all(value is True for value in questions.values())


def test_outputs_and_finding_taxonomy_are_bound() -> None:
    data = load_design()
    assert all(value is True for value in data["required_outputs"].values())
    assert set(data["allowed_integration_findings"]) == {
        "LEGITIMATE_SEPARATION",
        "PIPELINE_BYPASS",
        "STALE_AUTHORITY",
        "CALIBRATION_DEFECT",
        "MULTIPLE_CONTRIBUTING_CAUSES",
        "UNRESOLVED",
    }


def test_fail_closed_and_all_execution_boundaries_closed() -> None:
    data = load_design()
    assert all(value is True for value in data["fail_closed_rules"].values())
    assert all(value is False for value in data["boundaries"].values())
    assert data["fail_closed_rules"]["do_not_execute_superseded_decision_conflict_runtime_authorization"] is True
    assert data["boundaries"]["final_action_policy_authorized"] is False
    assert data["boundaries"]["runtime_implementation_authorized"] is False


def test_design_decision_and_next_decision() -> None:
    data = load_design()
    assert data["design_decision"] == "APPROVE_METALS_FINAL_DECISION_ARBITRATION_EVIDENCE_AUDIT_DESIGN_FOR_READ_ONLY_EXECUTION_AUTHORIZATION_CONSIDERATION"
    assert data["next_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_ARBITRATION_EVIDENCE_AUDIT"
