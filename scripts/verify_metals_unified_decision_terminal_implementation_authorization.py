from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config/metals/unified_decision_terminal_implementation_authorization.json"

EXPECTED_ID = "METALS-UNIFIED-DECISION-TERMINAL-IMPLEMENTATION-AUTHORIZATION-1"
EXPECTED_DESIGN_ID = "METALS-UNIFIED-DECISION-TERMINAL-REDESIGN-DESIGN-1"
EXPECTED_HEAD = "f1cfb0f3d48b08751d3abc092b3b15c8c2a6bce5"
EXPECTED_DB = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_PUB = "metals-v3-commodity-explanation-r4-20260826"
EXPECTED_FP = "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
EXPECTED_FILES = sorted([
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
    "foundation/production/dashboard_assets/recommendation_visual.css",
])


def all_true(mapping: dict) -> bool:
    return bool(mapping) and all(value is True for value in mapping.values())


def main() -> None:
    data = json.loads(AUTH.read_text(encoding="utf-8-sig"))
    boundary = data["authorization_boundary"]
    downstream_closed = all(
        value is False
        for key, value in boundary.items()
        if key != "runtime_implementation_authorized"
    )
    result = {
        "status": "PASS",
        "read_only": True,
        "authorization_id_bound": data["authorization_id"] == EXPECTED_ID,
        "source_design_bound": data["source_design_id"] == EXPECTED_DESIGN_ID,
        "source_head_bound": data["source_design_head"] == EXPECTED_HEAD,
        "database_sha_bound": data["source_database_sha256"] == EXPECTED_DB,
        "active_r4_bound": data["active_hosted_publication"]["publication_id"] == EXPECTED_PUB,
        "active_r4_fingerprint_bound": data["active_hosted_publication"]["content_fingerprint"] == EXPECTED_FP,
        "active_r4_count_bound": int(data["active_hosted_publication"]["record_count"]) == 12477,
        "runtime_file_scope_exact": sorted(data["authorized_runtime_files"]) == EXPECTED_FILES,
        "required_behavior_all_true": all_true(data["required_implementation_behavior"]),
        "semantic_guardrails_all_true": all_true(data["semantic_guardrails"]),
        "runtime_implementation_authorized": boundary["runtime_implementation_authorized"] is True,
        "hosted_write_not_authorized": boundary["hosted_publication_write_authorized"] is False,
        "database_write_not_authorized": boundary["analytical_database_write_authorized"] is False,
        "forecast_refresh_not_authorized": boundary["forecast_refresh_authorized"] is False,
        "model_refresh_not_authorized": boundary["model_refresh_authorized"] is False,
        "csp_cleanup_not_authorized": boundary["csp_cleanup_authorized"] is False,
        "pr_not_authorized": boundary["pull_request_authorized"] is False,
        "main_deploy_not_authorized": boundary["main_deployment_authorized"] is False,
        "downstream_boundaries_closed": downstream_closed,
        "decision_bound": data["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_UNIFIED_DECISION_TERMINAL_IMPLEMENTATION",
        "next_decision_bound": data["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_UNIFIED_DECISION_TERMINAL",
    }
    if not all(value is True for key, value in result.items() if key not in {"status"}):
        result["status"] = "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
