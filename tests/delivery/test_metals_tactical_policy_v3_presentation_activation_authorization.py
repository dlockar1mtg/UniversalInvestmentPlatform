from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_presentation_activation_authorization.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_presentation_activation_authorization.py"


def load_auth():
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_and_verifier_parse():
    compile(VERIFIER_PATH.read_text(encoding="utf-8"), str(VERIFIER_PATH), "exec")
    auth = load_auth()
    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-PRESENTATION-ACTIVATION-AUTHORIZATION-1"
    assert auth["source_design_id"] == "METALS-TACTICAL-POLICY-V3-PRESENTATION-ACTIVATION-AUTHORIZATION-DESIGN-1"
    assert auth["source_design_head"] == "ddba473097b1e7ae3656bd0f327942a98b847c0a"


def test_authorization_binds_certified_source_authorities():
    auth = load_auth()
    assert auth["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert auth["source_state_sha256"] == "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
    assert auth["source_manifest_sha256"] == "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"


def test_authorizes_implementation_not_activation():
    auth = load_auth()
    assert auth["authorization_decision"] == "AUTHORIZE_METALS_V3_PRESENTATION_IMPLEMENTATION_ONLY"
    impl = auth["authorized_presentation_implementation"]
    assert impl["record_type"] == "tactical_state"
    assert impl["domain_id"] == "metals"
    assert impl["source_relation"] == "metals_tactical_state_current"
    assert impl["presentation_publication_implementation_authorized"] is True
    assert impl["non_active_publication_validation_authorized"] is True
    boundary = auth["authorization_boundary"]
    assert boundary["presentation_activation_authorization_created"] is True
    assert boundary["presentation_publication_implementation_authorized"] is True
    assert boundary["presentation_activation_authorized"] is False
    assert boundary["presentation_activation_executed"] is False


def test_preserves_existing_decision_authorities():
    controls = load_auth()["required_implementation_controls"]
    for key in (
        "existing_recommendation_records_preserved",
        "existing_forecast_records_preserved",
        "existing_risk_records_preserved",
        "native_recommendation_preserved",
        "cross_domain_ordering_preserved",
        "tactical_state_visually_separate_from_long_term_thesis",
        "bil_reference_control_not_presented_as_opportunity",
    ):
        assert controls[key] is True


def test_implementation_is_read_only_to_analytical_duckdb_and_fails_closed():
    controls = load_auth()["required_implementation_controls"]
    assert controls["analytical_duckdb_read_only"] is True
    assert controls["missing_or_unknown_tactical_state_fails_closed"] is True
    assert controls["source_database_hash_verified_before_publication_build"] is True
    assert controls["source_lineage_verified_before_publication_build"] is True


def test_semantic_guardrails_stay_locked():
    guardrails = load_auth()["semantic_guardrails"]
    assert all(value is True for value in guardrails.values())
    assert guardrails["tactical_state_is_not_long_term_recommendation"] is True
    assert guardrails["no_tactical_overlay_is_not_sell_signal"] is True
    assert guardrails["no_tactical_overlay_is_not_allocation_instruction"] is True


def test_all_other_downstream_authorities_remain_false():
    boundary = load_auth()["authorization_boundary"]
    for key in (
        "presentation_activation_authorized",
        "presentation_activation_executed",
        "analytical_database_write_authorized",
        "second_production_database_write_authorized",
        "network_collection_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        assert boundary[key] is False


def test_next_decision_is_implementation():
    assert load_auth()["next_decision"] == "IMPLEMENT_METALS_TACTICAL_POLICY_V3_PRESENTATION_PUBLICATION_AND_UI"
