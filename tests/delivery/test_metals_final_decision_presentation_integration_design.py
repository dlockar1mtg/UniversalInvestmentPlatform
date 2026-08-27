from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "final_decision_presentation_integration_design.json"


def load_design() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_identity_and_source_bindings() -> None:
    design = load_design()
    assert design["design_id"] == "METALS-FINAL-DECISION-PRESENTATION-INTEGRATION-DESIGN-1"
    assert design["source_governed_head"] == "b621c661f9e1e2976e0c69b565a4b8e179a9aeac"
    assert design["source_policy_implementation_id"] == "METALS-FINAL-DECISION-ARBITRATION-IMPLEMENTATION-1"
    assert design["source_active_publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert design["source_active_publication_record_count"] == 12477


def test_exact_actions_and_watch_conflicts() -> None:
    actions = load_design()["certified_final_actions"]
    assert len(actions) == 12
    assert actions["metals:commodity:gold"] == "HOLD"
    assert actions["metals:commodity:uranium"] == "HOLD"
    assert actions["metals:vehicle:BIL"] == "REFERENCE_CONTROL"
    for asset in ("COPX", "CPER", "URA"):
        assert actions[f"metals:vehicle:{asset}"] == "HOLD"
    for asset in ("GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV"):
        assert actions[f"metals:vehicle:{asset}"] == "WATCH"
    assert "DECISION_CONFLICT" not in set(actions.values())


def test_projection_is_versioned_and_minimally_mutating() -> None:
    strategy = load_design()["integration_strategy"]
    assert strategy["integration_layer"] == "VERSIONED_PRESENTATION_PUBLICATION"
    assert strategy["source_publication_strategy"] == "CLONE_CURRENT_ACTIVE_PUBLICATION_AND_MUTATE_ONLY_THE_TWELVE_MAPPED_METALS_RECOMMENDATION_PAYLOADS"
    assert strategy["active_publication_mutation"] is False
    assert strategy["analytical_database_mutation"] is False
    assert strategy["read_api_change_required"] is False
    assert strategy["presentation_schema_change_required"] is False
    assert strategy["non_target_record_mutation_allowed"] is False
    assert strategy["target_record_count"] == 12
    assert strategy["expected_total_record_count_after_projection"] == 12477
    assert strategy["atomic_stage_validate_activate_required"] is True
    assert strategy["failed_replacement_must_preserve_last_good_active_publication"] is True


def test_payload_semantics_preserve_native_evidence() -> None:
    semantics = load_design()["recommendation_payload_semantics"]
    assert semantics["recommendation_field_becomes_final_user_facing_action"] is True
    assert semantics["native_recommendation_field_preserves_pre_integration_recommendation"] is True
    assert semantics["final_action_field_added"] is True
    assert semantics["final_action_rationale_class_field_added"] is True
    assert semantics["policy_authority_label_field_added"] is True
    assert semantics["forward_validation_status_field_added"] is True
    assert semantics["decision_conflict_is_final_action_field_added"] is True
    assert semantics["decision_conflict_is_final_action_value"] is False
    assert semantics["all_existing_non_recommendation_payload_values_preserved"] is True
    assert semantics["native_model_or_forecast_recompute_prohibited"] is True


def test_projection_invariants_all_fail_closed() -> None:
    invariants = load_design()["required_projection_invariants"]
    assert len(invariants) == 16
    assert all(value is True for value in invariants.values())


def test_output_contract_exact() -> None:
    outputs = load_design()["required_outputs_for_future_rehearsal"]
    assert set(outputs) == {
        "presentation_projection_plan_json",
        "twelve_target_payload_delta_json",
        "non_target_preservation_summary_json",
        "candidate_publication_manifest_json",
        "candidate_publication_validation_json",
        "rehearsal_summary_json",
    }
    assert all(value is True for value in outputs.values())


def test_all_execution_boundaries_closed() -> None:
    boundaries = load_design()["boundaries"]
    assert len(boundaries) == 17
    assert all(value is False for value in boundaries.values())


def test_next_decision_is_rehearsal_authorization_only() -> None:
    design = load_design()
    assert design["design_decision"] == "APPROVE_METALS_FINAL_DECISION_PRESENTATION_INTEGRATION_DESIGN_FOR_REHEARSAL_AUTHORIZATION_CONSIDERATION"
    assert design["next_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_PRESENTATION_PROJECTION_REHEARSAL"
