from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_production_database_write_review.json"

EXPECTED_POSTWRITE_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"


def main() -> int:
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    if review.get("review_id") != "METALS-TACTICAL-POLICY-V3-PRODUCTION-DATABASE-WRITE-REVIEW-1":
        raise RuntimeError("unexpected production database write review ID")
    if review.get("source_authorization_id") != "METALS-TACTICAL-POLICY-V3-ONE-BOUNDED-PRODUCTION-DATABASE-WRITE-AUTHORIZATION-1":
        raise RuntimeError("unexpected source write authorization")
    if review.get("source_authorization_head") != "4d9cbfe35d8f564c2a524fa0ddd7b00a2cb6a2e9":
        raise RuntimeError("unexpected source authorization HEAD")
    if review.get("source_state_sha256") != EXPECTED_STATE_SHA:
        raise RuntimeError("review state SHA binding changed")
    if review.get("source_manifest_sha256") != EXPECTED_MANIFEST_SHA:
        raise RuntimeError("review manifest SHA binding changed")
    if review.get("postwrite_database_sha256") != EXPECTED_POSTWRITE_DB_SHA:
        raise RuntimeError("review post-write database SHA binding changed")

    observed = review.get("observed_production_state", {})
    expected_counts = {
        "history_row_count": 11,
        "current_row_count": 11,
        "opportunity_row_count": 10,
        "reference_control_row_count": 1,
        "neutral_row_count": 11,
        "directional_opportunity_row_count": 0,
        "distinct_state_hash_count": 1,
        "distinct_manifest_hash_count": 1,
        "exact_import_id_count": 1,
    }
    for key, expected in expected_counts.items():
        if int(observed.get(key, -1)) != expected:
            raise RuntimeError(f"unexpected observed production count: {key}")
    for key in (
        "authorization_consumed",
        "second_execution_forbidden",
        "history_append_only",
        "source_lineage_verified",
    ):
        if observed.get(key) is not True:
            raise RuntimeError(f"required observed production control is not true: {key}")
    if observed.get("history_table") != "metals_tactical_state_history":
        raise RuntimeError("unexpected production history table")
    if observed.get("current_view") != "metals_tactical_state_current":
        raise RuntimeError("unexpected production current view")

    for key, value in review.get("semantic_findings", {}).items():
        if value is not True:
            raise RuntimeError(f"semantic finding is not true: {key}")

    if review.get("review_decision") != "PRODUCTION_DATABASE_WRITE_CERTIFIED_FOR_PRESENTATION_ACTIVATION_CONSIDERATION":
        raise RuntimeError("unexpected production database write review decision")

    controls = review.get("controls", {})
    if controls.get("production_database_write_certified") is not True:
        raise RuntimeError("production database write not certified")
    if controls.get("production_database_write_authorization_consumed") is not True:
        raise RuntimeError("one-time production authorization not marked consumed")
    if controls.get("presentation_activation_consideration_authorized") is not True:
        raise RuntimeError("presentation activation consideration not authorized")
    for key in (
        "second_production_database_write_authorized",
        "presentation_activation_authorized",
        "presentation_activation_executed",
        "network_collection_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"downstream authority prematurely enabled: {key}")

    if review.get("next_decision") != "DESIGN_METALS_TACTICAL_POLICY_V3_PRESENTATION_ACTIVATION_AUTHORIZATION":
        raise RuntimeError("unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "review_decision": review["review_decision"],
        "postwrite_database_sha256": EXPECTED_POSTWRITE_DB_SHA,
        "source_state_sha256": EXPECTED_STATE_SHA,
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA,
        "history_row_count": 11,
        "current_row_count": 11,
        "opportunity_row_count": 10,
        "reference_control_row_count": 1,
        "neutral_row_count": 11,
        "directional_opportunity_row_count": 0,
        "authorization_consumed": True,
        "second_production_database_write_authorized": False,
        "presentation_activation_consideration_authorized": True,
        "presentation_activation_authorized": False,
        "next_decision": review["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
