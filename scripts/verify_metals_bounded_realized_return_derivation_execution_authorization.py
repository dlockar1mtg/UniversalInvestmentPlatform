from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "bounded_realized_return_derivation_execution_authorization.json"

auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
findings = auth["certified_readiness_findings"]
behavior = auth["required_execution_behavior"]
outputs = auth["required_outputs"]
boundary = auth["authorization_boundary"]

expected_outputs = {
    "realized_return_rows_csv",
    "realized_return_rows_json",
    "derivation_lineage_json",
    "coverage_summary_json",
    "missing_future_price_register_json",
    "consumed_interval_annotation_json",
    "derivation_summary_json",
}

checks = {
    "read_only_inputs": True,
    "authorization_id_bound": auth["authorization_id"] == "METALS-BOUNDED-REALIZED-RETURN-DERIVATION-EXECUTION-AUTHORIZATION-1",
    "source_design_bound": auth["source_design_id"] == "METALS-BOUNDED-REALIZED-RETURN-DERIVATION-DESIGN-1",
    "source_head_bound": auth["source_design_head"] == "6d61723d19fb781cfe3fc13d5dc0c9702e3e0d3a",
    "source_audit_bound": auth["source_readiness_audit_id"] == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-AUDIT-1",
    "database_sha_bound": auth["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
    "readiness_bound": findings["readiness_finding"] == "READY_AFTER_REALIZED_RETURN_DERIVATION",
    "joinability_bound": findings["joinable_asset_horizon_row_count"] == 48 and findings["history_join_recovery_row_count"] == 0,
    "realized_outcome_missing_bound": findings["existing_realized_outcome_present"] is False and findings["realized_return_derivation_required"] is True,
    "execution_behavior_all_true": len(behavior) == 16 and all(value is True for value in behavior.values()),
    "required_outputs_exact": set(outputs) == expected_outputs and len(outputs) == 7,
    "required_outputs_all_true": set(outputs) == expected_outputs and all(value is True for value in outputs.values()),
    "derivation_authorized": boundary["bounded_realized_return_derivation_authorized"] is True,
    "local_evidence_write_authorized": boundary["local_evidence_artifact_write_authorized"] is True,
    "all_other_execution_boundaries_closed": all(
        value is False
        for key, value in boundary.items()
        if key not in {"bounded_realized_return_derivation_authorized", "local_evidence_artifact_write_authorized"}
    ),
    "decision_bound": auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_REALIZED_RETURN_DERIVATION",
    "next_decision_bound": auth["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_METALS_REALIZED_RETURN_DERIVATION",
}

status = "PASS" if all(checks.values()) else "FAIL"
print(json.dumps({**checks, "status": status}, indent=2, sort_keys=True))
raise SystemExit(0 if status == "PASS" else 1)
