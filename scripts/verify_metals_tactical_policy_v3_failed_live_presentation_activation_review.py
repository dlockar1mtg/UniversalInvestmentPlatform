from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "tactical_policy_v3_failed_live_presentation_activation_review.json"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def main() -> int:
    review = json.loads(PATH.read_text(encoding="utf-8"))
    assert review["review_id"] == "METALS-TACTICAL-POLICY-V3-FAILED-LIVE-PRESENTATION-ACTIVATION-REVIEW-1"
    assert review["source_authorization_id"] == "METALS-TACTICAL-POLICY-V3-LIVE-PRESENTATION-ACTIVATION-AUTHORIZATION-1"
    assert review["source_authorization_consumed"] is True
    assert review["source_database_sha256"] == EXPECTED_DB_SHA
    assert review["failed_target_publication_exists"] is False
    assert review["failed_target_record_count"] == 0
    assert review["failed_target_tactical_state_count"] == 0
    assert review["hosted_state"]["active_pointer_count"] == 1
    assert review["hosted_state"]["active_status_count"] == 1
    assert review["hosted_state"]["hosted_state_preserved"] is True
    assert review["hosted_state"]["partial_hosted_write_detected"] is False
    assert review["controls"]["consumed_authorization_may_be_reused"] is False
    assert review["controls"]["failed_target_publication_may_be_reused"] is False
    assert review["controls"]["new_activation_authorization_may_be_considered"] is True
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
        assert review["controls"][key] is False
    assert review["next_decision"] == "CONSIDER_FRESH_METALS_TACTICAL_POLICY_V3_LIVE_PRESENTATION_ACTIVATION_AUTHORIZATION"
    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "source_authorization_consumed": True,
        "failed_target_publication_exists": False,
        "partial_hosted_write_detected": False,
        "preserved_active_publication_id": review["preserved_active_publication"]["publication_id"],
        "source_database_sha256": review["source_database_sha256"],
        "new_activation_authorization_may_be_considered": True,
        "next_decision": review["next_decision"],
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
