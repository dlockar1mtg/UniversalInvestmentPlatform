from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "docs"
    / "project_control"
    / "generated"
    / "r1_refresh_orchestration"
    / "r1_refresh_orchestration_certification.json"
)


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_r1_certification_status_and_sequence():
    evidence = _evidence()
    assert evidence["certification_status"] == (
        "UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACT_CERTIFICATION_PASS"
    )
    assert evidence["sequence"]["next_milestone"] == (
        "UIP_R2_REFRESHED_DATA_REHEARSAL"
    )
    assert evidence["sequence"]["following_milestone"] == (
        "UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW"
    )
    assert evidence["sequence"]["r3_hard_gate_before_e1_or_dashboard_decision_logic"] is True


def test_r1_certification_preserves_domain_ownership():
    evidence = _evidence()
    domains = evidence["domain_boundaries"]
    assert set(domains) == {"crypto", "metals", "mtg"}
    assert domains["mtg"]["direct_uip_collector_invocation_authorized"] is False
    assert domains["crypto"]["direct_uip_collector_invocation_authorized"] is False
    assert domains["metals"]["producer_trigger"] == "uip_native_entrypoint"
    assert all(value["native_semantics_authoritative"] for value in domains.values())


def test_r1_certification_keeps_decision_authority_closed():
    controls = _evidence()["global_controls"]
    assert controls["cross_asset_ranking_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False
    assert controls["missing_authority_may_be_synthesized"] is False
    assert controls["partial_activation_authorized"] is False


def test_r1_certification_does_not_claim_fresh_output_certification():
    scope = _evidence()["scope_boundary"]
    assert scope["fresh_domain_outputs_certified_by_r1"] is False
    assert scope["real_refresh_performed_by_r1"] is False
    assert scope["production_database_activation_performed_by_r1"] is False
    assert scope["native_domain_models_changed"] is False
    assert scope["cross_asset_decision_model_created"] is False
