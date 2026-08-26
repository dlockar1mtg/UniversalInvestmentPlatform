from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "config" / "metals" / "bounded_realized_return_derivation_design.json"

payload = json.loads(DESIGN.read_text(encoding="utf-8"))

checks = {
    "read_only": True,
    "design_id_bound": payload.get("design_id") == "METALS-BOUNDED-REALIZED-RETURN-DERIVATION-DESIGN-1",
    "source_head_bound": payload.get("source_governed_head") == "0baa85e6c1a7ade3f9f8d7ea7c880e51e6a7552b",
    "source_audit_bound": payload.get("source_readiness_audit_id") == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-AUDIT-1",
    "database_sha_bound": payload.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
    "readiness_bound": payload.get("certified_readiness_findings", {}).get("readiness_finding") == "READY_AFTER_REALIZED_RETURN_DERIVATION",
    "joinability_bound": payload.get("certified_readiness_findings", {}).get("joinable_asset_horizon_row_count") == 48 and payload.get("certified_readiness_findings", {}).get("history_join_recovery_row_count") == 0,
    "realized_outcome_missing_bound": payload.get("certified_readiness_findings", {}).get("existing_realized_outcome_present") is False and payload.get("certified_readiness_findings", {}).get("realized_return_derivation_required") is True,
    "method_all_true": all(value is True for value in payload.get("required_method", {}).values()),
    "consumed_holdout_rules_all_true": all(value is True for value in payload.get("consumed_holdout_rules", {}).values()),
    "required_outputs_all_true": all(value is True for value in payload.get("required_outputs", {}).values()),
    "all_execution_boundaries_closed": all(value is False for value in payload.get("boundaries", {}).values()),
    "decision_bound": payload.get("design_decision") == "APPROVE_BOUNDED_METALS_REALIZED_RETURN_DERIVATION_DESIGN_FOR_EXECUTION_AUTHORIZATION_CONSIDERATION",
    "next_decision_bound": payload.get("next_decision") == "AUTHORIZE_BOUNDED_METALS_REALIZED_RETURN_DERIVATION",
}

result = {**checks, "status": "PASS" if all(checks.values()) else "FAIL"}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
