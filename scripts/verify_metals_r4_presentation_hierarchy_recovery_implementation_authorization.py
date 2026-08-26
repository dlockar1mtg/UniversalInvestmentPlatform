from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "r4_presentation_hierarchy_recovery_implementation_authorization.json"
DESIGN_PATH = ROOT / "config" / "metals" / "r4_presentation_hierarchy_recovery_design.json"

EXPECTED_AUTH_ID = "METALS-r4-PRESENTATION-HIERARCHY-RECOVERY-IMPLEMENTATION-AUTHORIZATION-1"
EXPECTED_DESIGN_ID = "METALS-r4-PRESENTATION-HIERARCHY-RECOVERY-DESIGN-1"
EXPECTED_DESIGN_HEAD = "b5ba7586a341dd75f5f335c28cf4fd75fc2f597d"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_R4 = "metals-v3-commodity-explanation-r4-20260826"
EXPECTED_FP = "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
EXPECTED_RUNTIME = sorted([
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/recommendation_visual.css",
])


def main() -> int:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    boundary = auth["authorization_boundary"]
    result = {
        "status": "PASS",
        "read_only": True,
        "authorization_id_bound": auth["authorization_id"] == EXPECTED_AUTH_ID,
        "source_design_bound": auth["source_design_id"] == EXPECTED_DESIGN_ID and design["design_id"] == EXPECTED_DESIGN_ID,
        "source_head_bound": auth["source_design_head"] == EXPECTED_DESIGN_HEAD,
        "database_sha_bound": auth["source_database_sha256"] == EXPECTED_DB_SHA,
        "active_r4_bound": auth["active_hosted_publication"]["publication_id"] == EXPECTED_R4,
        "active_r4_fingerprint_bound": auth["active_hosted_publication"]["content_fingerprint"] == EXPECTED_FP,
        "active_r4_count_bound": int(auth["active_hosted_publication"]["record_count"]) == 12477,
        "runtime_file_scope_exact": sorted(auth["authorized_runtime_files"]) == EXPECTED_RUNTIME,
        "required_behavior_all_true": all(value is True for value in auth["required_implementation_behavior"].values()),
        "semantic_guardrails_all_true": all(value is True for value in auth["semantic_guardrails"].values()),
        "runtime_implementation_authorized": boundary["runtime_implementation_authorized"] is True,
        "hosted_write_not_authorized": boundary["hosted_publication_write_authorized"] is False,
        "database_write_not_authorized": boundary["analytical_database_write_authorized"] is False,
        "forecast_refresh_not_authorized": boundary["forecast_refresh_authorized"] is False,
        "model_refresh_not_authorized": boundary["model_refresh_authorized"] is False,
        "csp_cleanup_not_authorized": boundary["csp_cleanup_authorized"] is False,
        "pr_not_authorized": boundary["pr_authorized"] is False,
        "main_deploy_not_authorized": boundary["main_deployment_authorized"] is False,
        "decision_bound": auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_r4_PRESENTATION_HIERARCHY_RECOVERY_IMPLEMENTATION",
        "next_decision_bound": auth["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_r4_PRESENTATION_HIERARCHY_RECOVERY",
    }
    result["downstream_boundaries_closed"] = all([
        result["hosted_write_not_authorized"],
        result["database_write_not_authorized"],
        result["forecast_refresh_not_authorized"],
        result["model_refresh_not_authorized"],
        result["csp_cleanup_not_authorized"],
        result["pr_not_authorized"],
        result["main_deploy_not_authorized"],
    ])

    checks = [value for key, value in result.items() if key not in {"status", "read_only"}]
    if not all(checks):
        result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
