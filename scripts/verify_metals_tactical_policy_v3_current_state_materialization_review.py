from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_current_state_materialization_review.json"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization.json"

EXPECTED_REVIEW_ID = "METALS-TACTICAL-POLICY-V3-CURRENT-STATE-MATERIALIZATION-REVIEW-1"
EXPECTED_AUTH_ID = "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-1"
EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(REVIEW_PATH.is_file(), "current-state materialization review is missing")
    require(AUTH_PATH.is_file(), "live-use authorization is missing")

    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    require(review["review_id"] == EXPECTED_REVIEW_ID, "unexpected review id")
    require(review["source_live_use_authorization_id"] == EXPECTED_AUTH_ID, "unexpected source authorization id")
    require(auth["authorization_id"] == EXPECTED_AUTH_ID, "source live-use authorization identity changed")
    require(auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_V3_LIVE_TACTICAL_INTERPRETATION", "source live-use authorization changed")
    require(auth["authorized_live_use"]["current_state_materialization_authorized"] is True, "current-state materialization is not authorized")
    require(auth["authorized_live_use"]["live_tactical_posture_authorized"] is True, "live tactical posture is not authorized")

    require(review["source_materialization_id"] == "METALS-TACTICAL-POLICY-V3-CURRENT-STATE-MATERIALIZATION-1", "unexpected source materialization id")
    require(review["source_materialization_state_sha256"] == EXPECTED_STATE_SHA, "state hash binding changed")
    require(review["source_materialization_manifest_sha256"] == EXPECTED_MANIFEST_SHA, "manifest hash binding changed")
    require(review["source_materialization_as_of_date"] == "2026-08-21", "materialization as-of date changed")
    require(review["source_package_id"] == "metals-price-history-20260824", "source package changed")
    require(review["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "classifier version changed")
    require(review["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", "action mapping changed")

    scope = review["review_scope"]
    require(scope["semantic_review"] is True, "semantic review missing")
    require(scope["operational_review"] is True, "operational review missing")
    require(scope["production_persistence_consideration_only"] is True, "review scope is not bounded to persistence consideration")
    require(scope["presentation_activation_review"] is False, "presentation activation was improperly included")
    require(scope["database_write_execution"] is False, "database write execution was improperly included")
    require(scope["network_collection"] is False, "network collection was improperly included")
    require(scope["model_retraining"] is False, "model retraining was improperly included")

    observed = review["observed_materialization"]
    require(observed["row_count"] == 11, "unexpected observed row count")
    require(observed["opportunity_row_count"] == 10, "unexpected opportunity row count")
    require(observed["reference_control_row_count"] == 1, "unexpected reference-control row count")
    require(observed["directional_opportunity_row_count"] == 0, "directional opportunity count changed")
    require(observed["state_counts"] == {"NO_TACTICAL_OVERLAY": 11}, "state counts changed")
    require(observed["all_opportunity_rows_non_directional"] is True, "opportunity neutrality finding changed")
    require(observed["bil_reference_control_only"] is True, "BIL role changed")
    require(observed["point_in_time_state"] is True, "current state is not point-in-time")
    require(observed["price_basis"] == "UNADJUSTED_CLOSE", "price basis changed")

    for key, value in review["review_findings"].items():
        require(value is True, f"review finding is not TRUE: {key}")

    for key, value in review["interpretation_guardrails"].items():
        require(value is True, f"interpretation guardrail is not TRUE: {key}")

    require(review["review_decision"] == "CURRENT_STATE_MATERIALIZATION_APPROVED_FOR_PRODUCTION_PERSISTENCE_CONSIDERATION", "unexpected review decision")

    controls = review["controls"]
    require(controls["current_state_materialization_review_passed"] is True, "review PASS control missing")
    require(controls["production_persistence_consideration_authorized"] is True, "persistence consideration not authorized")
    for key in [
        "production_database_write_authorized",
        "production_database_write_executed",
        "presentation_activation_authorized",
        "presentation_activation_executed",
        "native_source_query_authorized",
        "network_collection_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ]:
        require(controls[key] is False, f"downstream authority prematurely enabled: {key}")

    require(review["next_decision"] == "DESIGN_METALS_TACTICAL_POLICY_V3_PRODUCTION_PERSISTENCE_AUTHORIZATION", "unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "review_id": review["review_id"],
        "review_decision": review["review_decision"],
        "as_of_date": review["source_materialization_as_of_date"],
        "state_sha256": review["source_materialization_state_sha256"],
        "manifest_sha256": review["source_materialization_manifest_sha256"],
        "row_count": observed["row_count"],
        "opportunity_row_count": observed["opportunity_row_count"],
        "directional_opportunity_row_count": observed["directional_opportunity_row_count"],
        "state_counts": observed["state_counts"],
        "production_persistence_consideration_authorized": controls["production_persistence_consideration_authorized"],
        "production_database_write_authorized": controls["production_database_write_authorized"],
        "presentation_activation_authorized": controls["presentation_activation_authorized"],
        "next_decision": review["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
