from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_failed_activation_review_closes_consumed_attempt_without_hosted_mutation():
    review = read_json("config/metals/tactical_policy_v3_failed_live_presentation_activation_review.json")
    assert review["review_id"] == "METALS-TACTICAL-POLICY-V3-FAILED-LIVE-PRESENTATION-ACTIVATION-REVIEW-1"
    assert review["source_authorization_consumed"] is True
    assert review["failed_target_publication_id"] == "metals-v3-live-tactical-20260825"
    assert review["failed_target_publication_exists"] is False
    assert review["failed_target_record_count"] == 0
    assert review["failed_target_tactical_state_count"] == 0
    assert review["hosted_state"]["partial_hosted_write_detected"] is False
    assert review["hosted_state"]["active_pointer_count"] == 1
    assert review["hosted_state"]["active_status_count"] == 1


def test_failed_activation_review_preserves_prior_hosted_active_publication():
    review = read_json("config/metals/tactical_policy_v3_failed_live_presentation_activation_review.json")
    active = review["preserved_active_publication"]
    assert active["publication_id"] == "dash-read-1-metals-price-history-dff98e56d27c"
    assert active["publication_status"] == "ACTIVE"
    assert active["content_fingerprint"] == "c8742b715c8e6d4120eea6a1d717c0d2ebe7a90e78339f7b17cb4e64ee3d831f"
    assert active["record_count"] == 12476


def test_failed_activation_review_requires_fresh_authorization():
    review = read_json("config/metals/tactical_policy_v3_failed_live_presentation_activation_review.json")
    controls = review["controls"]
    assert controls["consumed_authorization_may_be_reused"] is False
    assert controls["failed_target_publication_may_be_reused"] is False
    assert controls["new_activation_authorization_may_be_considered"] is True
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
        assert controls[key] is False
    assert review["next_decision"] == "CONSIDER_FRESH_METALS_TACTICAL_POLICY_V3_LIVE_PRESENTATION_ACTIVATION_AUTHORIZATION"
