from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_fresh_live_presentation_activation_authorization.json"
REVIEW = ROOT / "config" / "metals" / "tactical_policy_v3_failed_live_presentation_activation_review.json"

EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_FP = "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126"
EXPECTED_PREVIOUS_ACTIVE = "dash-read-1-metals-price-history-dff98e56d27c"
EXPECTED_FRESH_TARGET = "metals-v3-live-tactical-r2-20260825"


def main() -> int:
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    if auth["source_failed_activation_review_id"] != review["review_id"]:
        raise RuntimeError("Fresh authorization is not bound to failed-activation review.")
    if auth["source_database_sha256"] != EXPECTED_DB_SHA:
        raise RuntimeError("Fresh authorization DuckDB SHA changed.")
    if auth["certified_content_fingerprint"] != EXPECTED_FP:
        raise RuntimeError("Fresh authorization fingerprint changed.")
    if auth["preserved_pre_activation_hosted_authority"]["publication_id"] != EXPECTED_PREVIOUS_ACTIVE:
        raise RuntimeError("Preserved active publication changed.")
    if auth["fresh_target_publication_id"] != EXPECTED_FRESH_TARGET:
        raise RuntimeError("Fresh target publication ID changed.")
    if auth["failed_prior_publication_id_may_be_reused"] is not False:
        raise RuntimeError("Failed prior publication ID became reusable.")
    if auth["consumed_prior_authorization_may_be_reused"] is not False:
        raise RuntimeError("Consumed prior authorization became reusable.")
    if auth["execution_limit"] != 1 or auth["execution_is_one_time"] is not True:
        raise RuntimeError("Fresh authorization is not exactly one bounded execution.")
    for key, value in auth["preconsumption_requirements"].items():
        if value is not True:
            raise RuntimeError(f"Preconsumption requirement is not TRUE: {key}")
    if auth["authorization_boundary"]["fresh_live_presentation_activation_authorized"] is not True:
        raise RuntimeError("Fresh live activation is not authorized.")
    if auth["authorization_boundary"]["fresh_live_presentation_activation_executed"] is not False:
        raise RuntimeError("Fresh live activation is already marked executed.")
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
        if auth["authorization_boundary"][key] is not False:
            raise RuntimeError(f"Unauthorized downstream authority enabled: {key}")
    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "authorization_decision": auth["authorization_decision"],
        "source_database_sha256": auth["source_database_sha256"],
        "certified_content_fingerprint": auth["certified_content_fingerprint"],
        "preserved_active_publication_id": EXPECTED_PREVIOUS_ACTIVE,
        "fresh_target_publication_id": EXPECTED_FRESH_TARGET,
        "execution_limit": auth["execution_limit"],
        "fresh_live_presentation_activation_authorized": auth["authorization_boundary"]["fresh_live_presentation_activation_authorized"],
        "fresh_live_presentation_activation_executed": auth["authorization_boundary"]["fresh_live_presentation_activation_executed"],
        "analytical_database_write_authorized": auth["authorization_boundary"]["analytical_database_write_authorized"],
        "next_decision": auth["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
