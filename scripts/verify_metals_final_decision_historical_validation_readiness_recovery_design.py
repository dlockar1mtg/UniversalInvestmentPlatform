from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "metals" / "final_decision_historical_validation_readiness_recovery_design.json"


def main() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    checks = {
        "design_id_bound": data.get("design_id") == "METALS-FINAL-DECISION-HISTORICAL-VALIDATION-READINESS-RECOVERY-DESIGN-1",
        "source_head_bound": data.get("source_governed_head") == "b76cc6c219ec407b4c0eb386af386ae71fd1a502",
        "source_audit_bound": data.get("source_arbitration_audit_id") == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-1",
        "database_sha_bound": data.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "hosted_r4_bound": (
            data.get("active_hosted_publication_id") == "metals-v3-commodity-explanation-r4-20260826"
            and data.get("active_hosted_publication_fingerprint") == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
            and data.get("active_hosted_record_count") == 12477
        ),
        "legitimate_separation_bound": data.get("certified_arbitration_audit_findings", {}).get("integration_finding") == "LEGITIMATE_SEPARATION",
        "historical_not_ready_bound": data.get("certified_arbitration_audit_findings", {}).get("historical_validation_ready") is False,
        "arithmetic_pass_bound": data.get("certified_arbitration_audit_findings", {}).get("adjusted_arithmetic_status") == "PASS",
        "no_pipeline_bypass_bound": data.get("certified_arbitration_audit_findings", {}).get("pipeline_bypass_signal") is False,
        "no_stale_authority_bound": data.get("certified_arbitration_audit_findings", {}).get("stale_authority_signal") is False,
        "no_calibration_defect_bound": data.get("certified_arbitration_audit_findings", {}).get("calibration_defect_proven") is False,
        "one_final_action_required": all(data.get("final_decision_requirement", {}).values()),
        "historical_evidence_classes_all_true": all(data.get("required_historical_evidence_classes", {}).values()),
        "recovery_questions_all_true": all(data.get("required_recovery_questions", {}).values()),
        "validation_principles_all_true": all(data.get("required_validation_principles", {}).values()),
        "required_outputs_all_true": all(data.get("required_outputs", {}).values()),
        "readiness_taxonomy_bound": set(data.get("allowed_readiness_findings", [])) == {
            "READY_FOR_BOUNDED_HISTORICAL_VALIDATION",
            "READY_AFTER_REALIZED_RETURN_DERIVATION",
            "READY_AFTER_HISTORY_JOIN_RECOVERY",
            "INSUFFICIENT_HISTORICAL_EVIDENCE",
            "BLOCKED_BY_CONSUMED_HOLDOUT_CONSTRAINT",
            "MULTIPLE_READINESS_GAPS",
            "UNRESOLVED",
        },
        "all_execution_boundaries_closed": all(value is False for value in data.get("boundaries", {}).values()),
        "decision_bound": data.get("design_decision") == "APPROVE_METALS_FINAL_DECISION_HISTORICAL_VALIDATION_READINESS_RECOVERY_DESIGN_FOR_READ_ONLY_EXECUTION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": data.get("next_decision") == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_HISTORICAL_VALIDATION_READINESS_RECOVERY_AUDIT",
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    result = {"status": status, "read_only": True, **checks}
    print(json.dumps(result, indent=2, sort_keys=True))

    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
