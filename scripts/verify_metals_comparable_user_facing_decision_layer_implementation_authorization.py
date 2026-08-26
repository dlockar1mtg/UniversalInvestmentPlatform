from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "comparable_user_facing_decision_layer_implementation_authorization.json"

data = json.loads(PATH.read_text(encoding="utf-8"))

expected_hold = {
    "metals:commodity:gold",
    "metals:commodity:uranium",
    "metals:vehicle:COPX",
    "metals:vehicle:CPER",
    "metals:vehicle:URA",
}
expected_conflict = {
    "metals:vehicle:GLD",
    "metals:vehicle:IAU",
    "metals:vehicle:PPLT",
    "metals:vehicle:SGOL",
    "metals:vehicle:SIVR",
    "metals:vehicle:SLV",
}
expected_reference = {"metals:vehicle:BIL"}
expected_runtime = {
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/recommendation_visual.css",
}

boundary = data["authorization_boundary"]

checks = {
    "authorization_id_bound": data["authorization_id"] == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-IMPLEMENTATION-AUTHORIZATION-1",
    "source_design_bound": data["source_design_id"] == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-DESIGN-1",
    "source_head_bound": data["source_design_head"] == "3aac888df4f7e92a3d7fa11992b4ccda87644526",
    "source_audit_bound": data["source_semantic_audit_id"] == "METALS-DECISION-SEMANTICS-AUDIT-EXECUTION-1",
    "database_sha_bound": data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
    "hosted_r4_bound": data["active_hosted_publication_id"] == "metals-v3-commodity-explanation-r4-20260826" and data["active_hosted_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5" and int(data["active_hosted_record_count"]) == 12477,
    "hold_assets_exact": set(data["certified_primary_status_partition"]["HOLD"]) == expected_hold,
    "conflict_assets_exact": set(data["certified_primary_status_partition"]["DECISION_CONFLICT"]) == expected_conflict,
    "reference_control_exact": set(data["certified_primary_status_partition"]["REFERENCE_CONTROL"]) == expected_reference,
    "runtime_files_exact": set(data["authorized_runtime_files"]) == expected_runtime,
    "required_behavior_all_true": all(value is True for value in data["required_implementation_behavior"].values()),
    "semantic_guardrails_all_true": all(value is True for value in data["semantic_guardrails"].values()),
    "runtime_implementation_authorized": boundary["runtime_implementation_authorized"] is True,
    "normalized_status_persistence_not_authorized": boundary["normalized_status_persistence_authorized"] is False,
    "hosted_write_not_authorized": boundary["hosted_publication_write_authorized"] is False,
    "database_write_not_authorized": boundary["analytical_database_write_authorized"] is False,
    "forecast_refresh_not_authorized": boundary["forecast_refresh_authorized"] is False,
    "model_refresh_not_authorized": boundary["model_refresh_authorized"] is False,
    "recommendation_recompute_not_authorized": boundary["recommendation_recompute_authorized"] is False,
    "network_collection_not_authorized": boundary["network_collection_authorized"] is False,
    "csp_cleanup_not_authorized": boundary["csp_cleanup_authorized"] is False,
    "pr_not_authorized": boundary["pr_authorized"] is False,
    "main_deployment_not_authorized": boundary["main_deployment_authorized"] is False,
    "allocation_execution_not_authorized": boundary["allocation_or_execution_authorized"] is False,
    "decision_bound": data["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_COMPARABLE_USER_FACING_DECISION_LAYER_IMPLEMENTATION",
    "next_decision_bound": data["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_COMPARABLE_USER_FACING_DECISION_LAYER",
}
checks["downstream_boundaries_closed"] = all(
    boundary[key] is False
    for key in boundary
    if key != "runtime_implementation_authorized"
)

result = {
    "status": "PASS" if all(checks.values()) else "FAIL",
    "read_only": True,
    **checks,
}
print(json.dumps(result, indent=2, sort_keys=True))
if result["status"] != "PASS":
    raise SystemExit(1)
