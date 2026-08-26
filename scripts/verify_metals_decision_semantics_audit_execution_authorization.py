from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "decision_semantics_audit_execution_authorization.json"


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))

    expected_assets = {
        "metals:commodity:gold",
        "metals:commodity:uranium",
        "metals:vehicle:BIL",
        "metals:vehicle:COPX",
        "metals:vehicle:CPER",
        "metals:vehicle:GLD",
        "metals:vehicle:IAU",
        "metals:vehicle:PPLT",
        "metals:vehicle:SGOL",
        "metals:vehicle:SIVR",
        "metals:vehicle:SLV",
        "metals:vehicle:URA",
    }

    boundary = data["authorization_boundary"]

    checks = {
        "authorization_id_bound": data["authorization_id"] == "METALS-DECISION-SEMANTICS-AUDIT-EXECUTION-AUTHORIZATION-1",
        "source_design_bound": data["source_design_id"] == "METALS-DECISION-SEMANTICS-AUDIT-DESIGN-1",
        "source_head_bound": data["source_design_head"] == "753aafc44d5c41861ab6f357a728101bbc9faab7",
        "database_sha_bound": data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "asset_scope_exact": set(data["required_asset_scope"]) == expected_assets,
        "audit_columns_complete": len(data["required_audit_columns"]) == 19,
        "required_behavior_all_true": all(data["required_execution_behavior"].values()),
        "required_outputs_all_true": all(data["required_outputs"].values()),
        "read_only_audit_authorized": boundary["read_only_audit_execution_authorized"] is True,
        "runtime_change_not_authorized": boundary["runtime_change_authorized"] is False,
        "user_facing_status_change_not_authorized": boundary["user_facing_status_change_authorized"] is False,
        "normalized_status_persistence_not_authorized": boundary["normalized_status_persistence_authorized"] is False,
        "hosted_write_not_authorized": boundary["hosted_write_authorized"] is False,
        "database_write_not_authorized": boundary["database_write_authorized"] is False,
        "forecast_refresh_not_authorized": boundary["forecast_refresh_authorized"] is False,
        "model_refresh_not_authorized": boundary["model_refresh_authorized"] is False,
        "csp_cleanup_not_authorized": boundary["csp_cleanup_authorized"] is False,
        "pr_not_authorized": boundary["pr_authorized"] is False,
        "main_deploy_not_authorized": boundary["main_deploy_authorized"] is False,
        "allocation_execution_not_authorized": boundary["allocation_execution_authorized"] is False,
        "decision_bound": data["authorization_decision"] == "AUTHORIZE_READ_ONLY_METALS_DECISION_SEMANTICS_AUDIT",
        "next_decision_bound": data["next_decision"] == "EXECUTE_AND_CERTIFY_READ_ONLY_METALS_DECISION_SEMANTICS_AUDIT",
    }

    closed = all(
        value is False
        for key, value in boundary.items()
        if key != "read_only_audit_execution_authorized"
    )
    checks["downstream_boundaries_closed"] = closed

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "read_only": True,
        **checks,
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
