from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "final_decision_historical_validation_readiness_recovery_audit_execution_authorization.json"


def main() -> None:
    data = json.loads(AUTH.read_text(encoding="utf-8"))
    boundary = data["authorization_boundary"]
    expected_findings = {
        "READY_FOR_BOUNDED_HISTORICAL_VALIDATION",
        "READY_AFTER_REALIZED_RETURN_DERIVATION",
        "READY_AFTER_HISTORY_JOIN_RECOVERY",
        "INSUFFICIENT_HISTORICAL_EVIDENCE",
        "BLOCKED_BY_CONSUMED_HOLDOUT_CONSTRAINT",
        "MULTIPLE_READINESS_GAPS",
        "UNRESOLVED",
    }
    checks = {
        "read_only": True,
        "authorization_id_bound": data["authorization_id"] == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-AUDIT-EXECUTION-AUTHORIZATION-1",
        "source_design_bound": data["source_design_id"] == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-DESIGN-1",
        "source_head_bound": data["source_design_head"] == "9c43488d3c9dea91df5b37380af1bdf61f290691",
        "source_audit_bound": data["source_arbitration_audit_id"] == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-1",
        "database_sha_bound": data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "hosted_r4_bound": data["active_hosted_publication_id"] == "metals-v3-commodity-explanation-r4-20260826" and data["active_hosted_record_count"] == 12477,
        "legitimate_separation_bound": data["certified_arbitration_findings"]["integration_finding"] == "LEGITIMATE_SEPARATION",
        "historical_not_ready_bound": data["certified_arbitration_findings"]["historical_validation_ready"] is False,
        "execution_behavior_all_true": all(data["required_execution_behavior"].values()),
        "required_outputs_all_true": all(data["required_outputs"].values()),
        "readiness_taxonomy_bound": set(data["allowed_readiness_findings"]) == expected_findings,
        "read_only_recovery_authorized": boundary["read_only_recovery_audit_execution_authorized"] is True,
        "local_evidence_write_authorized": boundary["local_evidence_artifact_write_authorized"] is True,
        "all_other_execution_boundaries_closed": all(
            value is False
            for key, value in boundary.items()
            if key not in {
                "read_only_recovery_audit_execution_authorized",
                "local_evidence_artifact_write_authorized",
            }
        ),
        "decision_bound": data["authorization_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_HISTORICAL_VALIDATION_READINESS_RECOVERY_AUDIT",
        "next_decision_bound": data["next_decision"] == "EXECUTE_AND_CERTIFY_READ_ONLY_METALS_FINAL_DECISION_HISTORICAL_VALIDATION_READINESS_RECOVERY_AUDIT",
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, **checks}, indent=2, sort_keys=True))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
