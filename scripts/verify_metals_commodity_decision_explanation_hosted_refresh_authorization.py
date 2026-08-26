from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config/metals/commodity_decision_explanation_hosted_refresh_authorization.json"

EXPECTED_ID = "METALS-COMMODITY-DECISION-EXPLANATION-HOSTED-REFRESH-AUTHORIZATION-1"
EXPECTED_HEAD = "5d11c2a8d1e660165a5c172c054fee39feb3c2a0"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_R3 = "metals-v3-decision-utility-r3-20260826"
EXPECTED_R3_FP = "e5f0bce3eb0181983e990e3de5795867dc53bf41c0d038b0d7302e722434b3ee"
EXPECTED_R4 = "metals-v3-commodity-explanation-r4-20260826"

payload = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

checks = {
    "authorization_id_bound": payload.get("authorization_id") == EXPECTED_ID,
    "source_head_bound": payload.get("source_implementation_head") == EXPECTED_HEAD,
    "database_sha_bound": payload.get("source_database_sha256") == EXPECTED_DB_SHA,
    "local_projection_record_count_bound": payload.get("source_local_projection_record_count") == 12477,
    "local_projection_explanation_count_bound": payload.get("source_local_projection_commodity_explanation_record_count") == 2,
    "active_r3_bound": payload.get("active_hosted_publication_before_refresh", {}).get("publication_id") == EXPECTED_R3,
    "active_r3_fingerprint_bound": payload.get("active_hosted_publication_before_refresh", {}).get("content_fingerprint") == EXPECTED_R3_FP,
    "target_r4_bound": payload.get("authorized_hosted_publication_after_refresh", {}).get("publication_id") == EXPECTED_R4,
    "target_r4_record_count_bound": payload.get("authorized_hosted_publication_after_refresh", {}).get("record_count") == 12477,
    "gold_context_bound": payload.get("authorized_hosted_publication_after_refresh", {}).get("gold_risk_context_level") == "ELEVATED",
    "uranium_unavailable_bound": payload.get("authorized_hosted_publication_after_refresh", {}).get("uranium_explanation_state") == "UNAVAILABLE",
    "hosted_write_authorized": payload.get("authorization_boundary", {}).get("hosted_publication_write_authorized") is True,
    "database_write_not_authorized": payload.get("authorization_boundary", {}).get("analytical_database_write_authorized") is False,
    "runtime_change_not_authorized": payload.get("authorization_boundary", {}).get("runtime_code_change_authorized") is False,
    "main_deploy_not_authorized": payload.get("authorization_boundary", {}).get("main_deployment_authorized") is False,
    "pr_not_authorized": payload.get("authorization_boundary", {}).get("pr_creation_authorized") is False,
    "semantic_guardrails_all_true": all(value is True for value in payload.get("semantic_guardrails", {}).values()),
    "required_refresh_behavior_all_true": all(value is True for value in payload.get("required_refresh_behavior", {}).values()),
}

closed_keys = {
    "analytical_database_write_authorized",
    "runtime_code_change_authorized",
    "main_deployment_authorized",
    "pr_creation_authorized",
    "model_retraining_authorized",
    "forecast_refresh_authorized",
    "network_collection_authorized",
    "allocation_policy_authorized",
    "automatic_execution_authorized",
}
checks["downstream_boundaries_closed"] = all(
    payload.get("authorization_boundary", {}).get(key) is False
    for key in closed_keys
)
checks["decision_bound"] = payload.get("authorization_decision") == "AUTHORIZE_ONE_BOUNDED_METALS_COMMODITY_EXPLANATION_HOSTED_PRESENTATION_REFRESH"
checks["next_decision_bound"] = payload.get("next_decision") == "EXECUTE_AND_CERTIFY_METALS_COMMODITY_EXPLANATION_HOSTED_PRESENTATION_REFRESH"

result = {
    "status": "PASS" if all(checks.values()) else "FAIL",
    "read_only": True,
    "authorization_id": payload.get("authorization_id"),
    **checks,
}

print(json.dumps(result, indent=2, sort_keys=True))

if result["status"] != "PASS":
    raise SystemExit(1)
