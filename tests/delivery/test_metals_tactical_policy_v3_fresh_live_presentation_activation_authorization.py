from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_fresh_authorization_binds_failed_attempt_review_and_new_target():
    auth = read_json("config/metals/tactical_policy_v3_fresh_live_presentation_activation_authorization.json")
    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-FRESH-LIVE-PRESENTATION-ACTIVATION-AUTHORIZATION-1"
    assert auth["source_failed_activation_review_id"] == "METALS-TACTICAL-POLICY-V3-FAILED-LIVE-PRESENTATION-ACTIVATION-REVIEW-1"
    assert auth["source_failed_activation_review_head"] == "434929e2e6718ec4fd3e81006d55fb901c428409"
    assert auth["fresh_target_publication_id"] == "metals-v3-live-tactical-r2-20260825"
    assert auth["failed_prior_publication_id"] == "metals-v3-live-tactical-20260825"
    assert auth["failed_prior_publication_id_may_be_reused"] is False
    assert auth["consumed_prior_authorization_may_be_reused"] is False


def test_fresh_authorization_preserves_certified_source_and_hosted_authority():
    auth = read_json("config/metals/tactical_policy_v3_fresh_live_presentation_activation_authorization.json")
    assert auth["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert auth["certified_content_fingerprint"] == "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126"
    assert auth["certified_record_count"] == 4181
    assert auth["certified_metals_tactical_state_count"] == 10
    preserved = auth["preserved_pre_activation_hosted_authority"]
    assert preserved["publication_id"] == "dash-read-1-metals-price-history-dff98e56d27c"
    assert preserved["publication_status"] == "ACTIVE"
    assert preserved["active_pointer_count"] == 1
    assert preserved["active_status_count"] == 1


def test_fresh_authorization_requires_hosted_preconditions_before_consumption():
    auth = read_json("config/metals/tactical_policy_v3_fresh_live_presentation_activation_authorization.json")
    for value in auth["preconsumption_requirements"].values():
        assert value is True
    assert auth["preconsumption_requirements"]["uiip_database_url_present"] is True
    assert auth["preconsumption_requirements"]["hosted_postgresql_connectivity_verified"] is True
    assert auth["preconsumption_requirements"]["preserved_active_publication_verified"] is True
    assert auth["preconsumption_requirements"]["fresh_target_publication_absent_verified"] is True
    assert auth["preconsumption_requirements"]["all_preconsumption_checks_must_complete_before_consumption_marker"] is True


def test_fresh_authorization_is_one_bounded_execution_with_downstream_boundaries_closed():
    auth = read_json("config/metals/tactical_policy_v3_fresh_live_presentation_activation_authorization.json")
    assert auth["authorization_decision"] == "AUTHORIZE_ONE_FRESH_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION"
    assert auth["execution_limit"] == 1
    assert auth["execution_is_one_time"] is True
    boundary = auth["authorization_boundary"]
    assert boundary["fresh_live_presentation_activation_authorized"] is True
    assert boundary["fresh_live_presentation_activation_executed"] is False
    for key in (
        "analytical_database_write_authorized",
        "second_metals_production_write_authorized",
        "network_collection_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        assert boundary[key] is False
    assert auth["next_decision"] == "EXECUTE_ONE_FRESH_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION"
