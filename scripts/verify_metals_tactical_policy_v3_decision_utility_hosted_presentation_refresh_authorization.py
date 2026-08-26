from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config/metals/tactical_policy_v3_decision_utility_hosted_presentation_refresh_authorization.json"


def main() -> None:
    payload = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    controls = payload.get("required_refresh_controls") or {}
    guardrails = payload.get("semantic_guardrails") or {}
    boundary = payload.get("authorization_boundary") or {}
    projection = payload.get("certified_local_projection") or {}
    prior = payload.get("expected_prior_active_publication") or {}
    refresh = payload.get("authorized_refresh") or {}

    result = {
        "status": "PASS",
        "read_only": True,
        "authorization_id": payload.get("authorization_id"),
        "authorization_decision": payload.get("authorization_decision"),
        "source_verifier_recovery_head": payload.get("source_verifier_recovery_head"),
        "local_projection_current_price_count": projection.get("current_price_record_count"),
        "local_projection_price_history_count": projection.get("price_history_record_count"),
        "local_projection_tactical_count": projection.get("tactical_opportunity_record_count"),
        "unadjusted_close_locked": projection.get("price_semantics") == "UNADJUSTED_CLOSE" and projection.get("history_value_field") == "close_usd",
        "prior_active_publication_bound": prior.get("publication_id") == "metals-v3-live-tactical-r2-20260825" and prior.get("content_fingerprint") == "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126",
        "new_publication_id_bound": refresh.get("new_publication_id") == "metals-v3-decision-utility-r3-20260826",
        "one_time_execution": refresh.get("execution_limit") == 1 and refresh.get("execution_is_one_time") is True,
        "stage_validate_activate_atomic": refresh.get("stage_new_publication") is True and refresh.get("validate_staged_publication_before_activation") is True and refresh.get("activate_staged_publication_atomically") is True,
        "required_controls_all_true": bool(controls) and all(value is True for value in controls.values()),
        "semantic_guardrails_all_true": bool(guardrails) and all(value is True for value in guardrails.values()),
        "hosted_refresh_authorized": boundary.get("hosted_presentation_refresh_authorized") is True,
        "hosted_refresh_executed": boundary.get("hosted_presentation_refresh_executed") is True,
        "analytical_database_write_authorized": boundary.get("analytical_database_write_authorized"),
        "main_deployment_authorized": boundary.get("main_deployment_authorized"),
        "pull_request_authorized": boundary.get("pull_request_authorized"),
        "next_decision": payload.get("next_decision"),
    }

    if payload.get("authorization_id") != "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-HOSTED-PRESENTATION-REFRESH-AUTHORIZATION-1":
        result["status"] = "FAIL"
    if payload.get("source_implementation_head") != "c3cfc37923296eefdfed6a689e412dc58168ede0":
        result["status"] = "FAIL"
    if payload.get("source_verifier_recovery_head") != "33862d476b282744c6e61f9d2fe78d5c6db3e0f3":
        result["status"] = "FAIL"
    if payload.get("source_database_sha256") != "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f":
        result["status"] = "FAIL"
    if projection.get("current_price_record_count") != 11 or projection.get("price_history_record_count") != 8283 or projection.get("tactical_opportunity_record_count") != 10:
        result["status"] = "FAIL"
    if not result["unadjusted_close_locked"] or not result["prior_active_publication_bound"] or not result["new_publication_id_bound"]:
        result["status"] = "FAIL"
    if not result["one_time_execution"] or not result["stage_validate_activate_atomic"]:
        result["status"] = "FAIL"
    if not result["required_controls_all_true"] or not result["semantic_guardrails_all_true"]:
        result["status"] = "FAIL"
    if result["hosted_refresh_authorized"] is not True or result["hosted_refresh_executed"] is not False:
        result["status"] = "FAIL"
    for key, value in boundary.items():
        if key in {"hosted_presentation_refresh_authorized", "hosted_presentation_refresh_executed"}:
            continue
        if value is not False:
            result["status"] = "FAIL"
    if payload.get("authorization_decision") != "AUTHORIZE_ONE_BOUNDED_HOSTED_PRESENTATION_REFRESH_FOR_METALS_DECISION_UTILITY":
        result["status"] = "FAIL"
    if payload.get("next_decision") != "IMPLEMENT_AND_EXECUTE_ONE_BOUNDED_HOSTED_PRESENTATION_REFRESH_FOR_METALS_DECISION_UTILITY":
        result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
