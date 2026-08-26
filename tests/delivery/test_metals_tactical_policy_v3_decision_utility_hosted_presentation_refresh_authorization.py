from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config/metals/tactical_policy_v3_decision_utility_hosted_presentation_refresh_authorization.json"


def payload() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_is_bound_to_certified_implementation_and_recovery() -> None:
    value = payload()
    assert value["authorization_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-HOSTED-PRESENTATION-REFRESH-AUTHORIZATION-1"
    assert value["source_implementation_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-COMPLETION-IMPLEMENTATION-1"
    assert value["source_implementation_head"] == "c3cfc37923296eefdfed6a689e412dc58168ede0"
    assert value["source_verifier_recovery_head"] == "33862d476b282744c6e61f9d2fe78d5c6db3e0f3"
    assert value["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_external_market_authority_hashes_are_locked() -> None:
    value = payload()
    assert value["source_price_package_id"] == "metals-price-history-20260824"
    assert value["source_current_price_sha256"] == "e18ece1a8dbc5b23f6ec7bb2d014822bdccd8a7f82fca0b6c23d5fda3bc8a4ed"
    assert value["source_price_history_sha256"] == "c3749acbcf3a6d11ee9a6ca392b8421e7654936af489fbb93a2f4ae659470f31"
    assert value["source_manifest_sha256"] == "82ead8e711e0fde4b30fa4e0e7196681e41e7f0ffa363af201c0ee0737473dcf"


def test_certified_local_projection_counts_and_semantics_are_locked() -> None:
    projection = payload()["certified_local_projection"]
    assert projection["current_price_record_count"] == 11
    assert projection["price_history_record_count"] == 8283
    assert projection["tactical_opportunity_record_count"] == 10
    assert projection["price_semantics"] == "UNADJUSTED_CLOSE"
    assert projection["history_value_field"] == "close_usd"
    assert projection["commodity_price_inference"] is False
    assert projection["analytical_database_write"] is False
    assert projection["hosted_publication_write"] is False


def test_prior_active_publication_is_fail_closed_bound() -> None:
    prior = payload()["expected_prior_active_publication"]
    assert prior == {
        "publication_id": "metals-v3-live-tactical-r2-20260825",
        "content_fingerprint": "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126",
        "record_count": 4181,
    }


def test_refresh_is_one_time_stage_validate_atomic_activate() -> None:
    refresh = payload()["authorized_refresh"]
    assert refresh["new_publication_id"] == "metals-v3-decision-utility-r3-20260826"
    assert refresh["execution_limit"] == 1
    assert refresh["execution_is_one_time"] is True
    assert refresh["stage_new_publication"] is True
    assert refresh["validate_staged_publication_before_activation"] is True
    assert refresh["activate_staged_publication_atomically"] is True
    assert refresh["verify_active_publication_after_switch"] is True
    assert refresh["supersede_prior_active_only_after_successful_switch"] is True


def test_all_refresh_controls_and_semantic_guardrails_are_required() -> None:
    value = payload()
    assert all(item is True for item in value["required_refresh_controls"].values())
    assert all(item is True for item in value["semantic_guardrails"].values())


def test_only_hosted_refresh_is_authorized_and_not_yet_executed() -> None:
    boundary = payload()["authorization_boundary"]
    assert boundary["hosted_presentation_refresh_authorized"] is True
    assert boundary["hosted_presentation_refresh_executed"] is False
    for key, value in boundary.items():
        if key in {"hosted_presentation_refresh_authorized", "hosted_presentation_refresh_executed"}:
            continue
        assert value is False, key


def test_authorization_decision_and_next_decision_are_exact() -> None:
    value = payload()
    assert value["authorization_decision"] == "AUTHORIZE_ONE_BOUNDED_HOSTED_PRESENTATION_REFRESH_FOR_METALS_DECISION_UTILITY"
    assert value["next_decision"] == "IMPLEMENT_AND_EXECUTE_ONE_BOUNDED_HOSTED_PRESENTATION_REFRESH_FOR_METALS_DECISION_UTILITY"
