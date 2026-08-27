from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "final_decision_presentation_stage_authorization.json"


def _doc():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_stage_authorization_identity_and_sources_are_locked():
    doc = _doc()
    assert doc["authorization_id"] == "METALS-FINAL-DECISION-PRESENTATION-STAGE-AUTHORIZATION-1"
    assert doc["source_integration_design_id"] == "METALS-FINAL-DECISION-PRESENTATION-INTEGRATION-DESIGN-1"
    assert doc["source_projection_rehearsal_id"] == "METALS-FINAL-DECISION-PRESENTATION-PROJECTION-REHEARSAL-1"
    assert doc["source_projection_rehearsal_governed_head"] == "1bf46d889f478fc0614467b503300a04fecfff8a"
    assert doc["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_stage_authorization_binds_source_and_candidate_publications():
    doc = _doc()
    assert doc["source_active_publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert doc["source_active_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
    assert doc["source_active_publication_record_count"] == 12477
    assert doc["certified_candidate_publication_id"] == "metals-final-decision-presentation-r1-20260827"
    assert doc["certified_candidate_content_fingerprint"] == "9de5edb450542be85dd68f3b0dd539dc520ef1f92b9de1b743672d7a6b1e289d"
    assert doc["certified_candidate_record_count"] == 12477


def test_stage_authorization_binds_rehearsal_accounting():
    doc = _doc()
    assert doc["certified_target_payload_mutation_count"] == 12
    assert doc["certified_recommendation_value_change_count"] == 9
    assert doc["certified_recommendation_value_retain_count"] == 3
    assert doc["certified_non_target_record_count"] == 12465
    assert doc["certified_non_target_canonical_mismatch_count"] == 0


def test_only_bounded_stage_capabilities_are_open():
    scope = _doc()["authorization_scope"]
    expected_open = {
        "read_active_presentation_authorized",
        "reconstruct_certified_candidate_in_memory_authorized",
        "hosted_candidate_stage_authorized",
        "hosted_candidate_validate_staged_authorized",
        "candidate_rejection_on_stage_validation_failure_authorized",
        "local_stage_evidence_artifact_write_authorized",
    }
    assert {key for key, value in scope.items() if value is True} == expected_open
    assert scope["hosted_activation_authorized"] is False
    assert scope["active_publication_mutation_authorized"] is False


def test_downstream_execution_remains_closed():
    scope = _doc()["authorization_scope"]
    for key in (
        "analytical_database_write_authorized",
        "non_presentation_hosted_database_write_authorized",
        "runtime_change_authorized",
        "recommendation_recompute_authorized",
        "forecast_refresh_authorized",
        "model_refresh_authorized",
        "network_collection_authorized",
        "pr_authorized",
        "main_deploy_authorized",
        "allocation_or_execution_authorized",
    ):
        assert scope[key] is False


def test_required_stage_behavior_is_complete_and_fail_closed():
    behavior = _doc()["required_stage_behavior"]
    assert len(behavior) == 24
    assert all(value is True for value in behavior.values())
    assert behavior["require_candidate_fingerprint_exactly_matches_certified_rehearsal"] is True
    assert behavior["prove_active_publication_pointer_unchanged_after_stage"] is True
    assert behavior["reject_only_certified_candidate_if_post_stage_validation_fails"] is True
    assert behavior["do_not_activate_candidate"] is True


def test_required_stage_outputs_are_exact():
    outputs = _doc()["required_outputs"]
    assert set(outputs) == {
        "presentation_stage_plan_json",
        "hosted_stage_write_receipt_json",
        "staged_candidate_validation_json",
        "active_publication_preservation_json",
        "presentation_stage_summary_json",
    }
    assert all(value is True for value in outputs.values())


def test_stage_decision_and_next_step_are_locked():
    doc = _doc()
    assert doc["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_DECISION_PRESENTATION_STAGE"
    assert doc["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_METALS_FINAL_DECISION_PRESENTATION_STAGE"
