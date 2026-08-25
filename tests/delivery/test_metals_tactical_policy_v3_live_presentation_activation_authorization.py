from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "config/metals/tactical_policy_v3_live_presentation_activation_authorization.json"
VERIFIER = ROOT / "scripts/verify_metals_tactical_policy_v3_live_presentation_activation_authorization.py"


def payload() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_live_activation_is_one_bounded_execution_only():
    p = payload()
    assert p["authorization_decision"] == "AUTHORIZE_ONE_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION"
    assert p["execution_limit"] == 1
    assert p["execution_is_one_time"] is True
    assert p["authorization_boundary"]["live_presentation_activation_authorized"] is True
    assert p["authorization_boundary"]["live_presentation_activation_executed"] is False


def test_authorization_binds_certified_non_active_publication():
    p = payload()
    certified = p["certified_non_active_publication"]
    assert p["source_implementation_head"] == "b52210de66169ebacb0afccf363f27e320c5624e"
    assert p["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert certified["content_fingerprint"] == "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126"
    assert certified["total_record_count"] == 4181
    assert certified["metals_tactical_state_count"] == 10


def test_activation_requires_stage_validation_and_atomic_switch():
    controls = payload()["required_execution_controls"]
    for key in (
        "source_duckdb_sha_must_match_before_stage",
        "staged_publication_fingerprint_must_match_certified_non_active_fingerprint",
        "staged_publication_record_count_must_match_certified_non_active_count",
        "prior_active_publication_must_remain_active_until_new_stage_validation_passes",
        "active_pointer_switch_must_be_atomic",
        "failure_before_activation_must_leave_prior_active_publication_unchanged",
        "failure_during_activation_must_rollback_pointer_switch",
        "post_activation_active_metadata_must_bind_source_database_sha",
        "post_activation_asset_detail_must_expose_tactical_state",
        "post_activation_recommendation_payload_must_remain_unmodified",
    ):
        assert controls[key] is True


def test_tactical_semantics_and_existing_authorities_remain_separate():
    p = payload()
    controls = p["required_execution_controls"]
    assert controls["bil_must_not_be_projected_as_tactical_opportunity"] is True
    assert controls["all_tactical_states_must_equal_no_tactical_overlay"] is True
    assert controls["all_tactical_regimes_must_equal_neutral_or_uncertain"] is True
    assert controls["existing_recommendation_records_must_remain_present"] is True
    assert controls["existing_forecast_records_must_remain_present"] is True
    assert controls["existing_risk_records_must_remain_present"] is True
    for value in p["semantic_guardrails"].values():
        assert value is True


def test_no_analytical_or_downstream_authority_is_added():
    boundary = payload()["authorization_boundary"]
    assert boundary["analytical_database_write_authorized"] is False
    assert boundary["second_production_database_write_authorized"] is False
    assert boundary["network_collection_authorized"] is False
    assert boundary["forecast_refresh_authorized"] is False
    assert boundary["model_retraining_authorized"] is False
    assert boundary["cross_domain_rank_authorized"] is False
    assert boundary["allocation_policy_authorized"] is False
    assert boundary["automatic_execution_authorized"] is False


def test_verifier_is_read_only_contract_checker():
    source = VERIFIER.read_text(encoding="utf-8")
    assert "read_only" in source
    assert "AUTHORIZE_ONE_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION" in source
    assert "IMPLEMENT_AND_EXECUTE_ONE_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION" in source
    assert "psycopg" not in source
    assert "duckdb.connect" not in source
