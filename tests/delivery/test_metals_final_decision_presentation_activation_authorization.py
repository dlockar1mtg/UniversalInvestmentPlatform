from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "final_decision_presentation_activation_authorization.json"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_identity_and_sources_are_bound():
    data = load()
    assert data["authorization_id"] == "METALS-FINAL-DECISION-PRESENTATION-ACTIVATION-AUTHORIZATION-1"
    assert data["source_stage_authorization_id"] == "METALS-FINAL-DECISION-PRESENTATION-STAGE-AUTHORIZATION-1"
    assert data["source_stage_governed_head"] == "96dac900d0a4a6d57e8f90741162aa777e0adfa9"
    assert data["source_stage_execution_id"] == "METALS-FINAL-DECISION-PRESENTATION-STAGE-1"


def test_active_and_candidate_authorities_are_exact():
    data = load()
    assert data["expected_current_active_publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert data["expected_current_active_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
    assert data["expected_current_active_publication_record_count"] == 12477
    assert data["authorized_candidate_publication_id"] == "metals-final-decision-presentation-r1-20260827"
    assert data["authorized_candidate_pre_activation_status"] == "STAGED"
    assert data["authorized_candidate_content_fingerprint"] == "9de5edb450542be85dd68f3b0dd539dc520ef1f92b9de1b743672d7a6b1e289d"
    assert data["authorized_candidate_record_count"] == 12477
    assert data["authorized_target_payload_count"] == 12
    assert data["authorized_final_action_counts"] == {"HOLD": 5, "WATCH": 6, "REFERENCE_CONTROL": 1}


def test_only_exact_activation_capabilities_are_open():
    data = load()
    scope = data["authorization_scope"]
    expected_open = {
        "read_current_active_publication_authorized",
        "read_staged_candidate_authorized",
        "validate_staged_candidate_pre_activation_authorized",
        "activate_exact_certified_candidate_authorized",
        "read_post_activation_state_authorized",
        "local_activation_evidence_artifact_write_authorized",
    }
    assert {k for k, v in scope.items() if v is True} == expected_open
    for key in (
        "activate_any_other_publication_authorized",
        "candidate_content_mutation_authorized",
        "candidate_restaging_authorized",
        "candidate_rejection_authorized",
        "manual_rollback_authorized",
        "analytical_database_write_authorized",
        "non_presentation_hosted_database_write_authorized",
        "runtime_code_change_authorized",
        "recommendation_recompute_authorized",
        "forecast_refresh_authorized",
        "model_refresh_authorized",
        "network_collection_authorized",
        "pr_authorized",
        "main_deploy_authorized",
        "allocation_or_execution_authorized",
    ):
        assert scope[key] is False


def test_activation_behavior_is_fail_closed_and_complete():
    data = load()
    behavior = data["required_activation_behavior"]
    assert len(behavior) == 28
    assert all(behavior.values())
    assert behavior["perform_exactly_one_activation_call"] is True
    assert behavior["do_not_attempt_rollback_without_separate_authorization"] is True
    assert behavior["verify_previous_active_publication_becomes_superseded"] is True


def test_outputs_are_exact():
    data = load()
    assert set(data["required_outputs"]) == {
        "presentation_activation_plan_json",
        "pre_activation_validation_json",
        "hosted_activation_receipt_json",
        "post_activation_validation_json",
        "previous_publication_supersession_json",
        "presentation_activation_summary_json",
    }
    assert all(data["required_outputs"].values())


def test_decision_and_next_are_exact():
    data = load()
    assert data["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_DECISION_PRESENTATION_ACTIVATION"
    assert data["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_METALS_FINAL_DECISION_PRESENTATION_ACTIVATION"
