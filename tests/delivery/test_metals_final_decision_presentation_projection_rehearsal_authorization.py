from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "final_decision_presentation_projection_rehearsal_authorization.json"
DESIGN_PATH = ROOT / "config" / "metals" / "final_decision_presentation_integration_design.json"


def load():
    return (
        json.loads(AUTH_PATH.read_text(encoding="utf-8")),
        json.loads(DESIGN_PATH.read_text(encoding="utf-8")),
    )


def test_authorization_identity_and_binding():
    auth, design = load()
    assert auth["authorization_id"] == "METALS-FINAL-DECISION-PRESENTATION-PROJECTION-REHEARSAL-AUTHORIZATION-1"
    assert auth["source_design_id"] == design["design_id"]
    assert auth["source_design_head"] == "71062dbee559ea21389f2408867dc921aafd3475"
    assert auth["source_database_sha256"] == design["source_database_sha256"]
    assert auth["source_active_publication_id"] == design["source_active_publication_id"]
    assert auth["source_active_publication_fingerprint"] == design["source_active_publication_fingerprint"]
    assert auth["source_active_publication_record_count"] == 12477


def test_only_read_only_rehearsal_scope_is_open():
    auth, _ = load()
    scope = auth["authorization_scope"]
    assert {k for k, v in scope.items() if v is True} == {
        "read_active_presentation_authorized",
        "local_in_memory_projection_authorized",
        "local_evidence_artifact_write_authorized",
    }
    for key in (
        "hosted_stage_authorized",
        "hosted_activation_authorized",
        "active_publication_mutation_authorized",
        "analytical_database_write_authorized",
        "hosted_database_write_authorized",
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


def test_rehearsal_behavior_is_exact_and_all_true():
    auth, _ = load()
    behavior = auth["required_rehearsal_behavior"]
    assert len(behavior) == 15
    assert all(behavior.values())
    assert behavior["clone_current_active_publication_in_memory"] is True
    assert behavior["mutate_exactly_twelve_mapped_metals_recommendation_payloads"] is True
    assert behavior["preserve_all_non_target_records_canonically"] is True
    assert behavior["preserve_total_record_count_12477"] is True
    assert behavior["prove_active_publication_unchanged_after_rehearsal"] is True
    assert behavior["do_not_modify_read_api"] is True


def test_required_outputs_match_design():
    auth, design = load()
    assert set(auth["required_outputs"]) == set(design["required_outputs_for_future_rehearsal"])
    assert all(auth["required_outputs"].values())


def test_decisions_are_bound():
    auth, _ = load()
    assert auth["authorization_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_PRESENTATION_PROJECTION_REHEARSAL"
    assert auth["next_decision"] == "EXECUTE_AND_CERTIFY_READ_ONLY_METALS_FINAL_DECISION_PRESENTATION_PROJECTION_REHEARSAL"
