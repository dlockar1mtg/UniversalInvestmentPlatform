from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "metals" / "final_decision_arbitration_evidence_audit_execution_authorization.json"

EXPECTED_ASSETS = {
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

EXPECTED_FINDINGS = {
    "LEGITIMATE_SEPARATION",
    "PIPELINE_BYPASS",
    "STALE_AUTHORITY",
    "CALIBRATION_DEFECT",
    "MULTIPLE_CONTRIBUTING_CAUSES",
    "UNRESOLVED",
}


def main() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    boundary = data["authorization_boundary"]
    execution = data["required_execution_behavior"]
    outputs = data["required_outputs"]
    fail_closed = data["fail_closed_rules"]
    superseded = data["superseded_runtime_authorization"]

    result = {
        "status": "PASS",
        "read_only": execution.get("read_only") is True,
        "authorization_id_bound": data.get("authorization_id") == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-EXECUTION-AUTHORIZATION-1",
        "source_design_bound": data.get("source_design_id") == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-DESIGN-1",
        "source_head_bound": data.get("source_design_head") == "86f785e2c1e4fe2d78949683c4c898fcce0d85c2",
        "database_sha_bound": data.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "hosted_r4_bound": (
            data.get("active_hosted_publication_id") == "metals-v3-commodity-explanation-r4-20260826"
            and data.get("active_hosted_publication_fingerprint") == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
            and data.get("active_hosted_record_count") == 12477
        ),
        "semantic_audit_bound": data.get("source_semantic_audit_id") == "METALS-DECISION-SEMANTICS-AUDIT-EXECUTION-1",
        "asset_scope_exact": set(data.get("required_asset_scope", [])) == EXPECTED_ASSETS,
        "superseded_runtime_execution_prohibited": (
            superseded.get("authorization_id") == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-IMPLEMENTATION-AUTHORIZATION-1"
            and superseded.get("state") == "SUPERSEDED_BY_FINAL_DECISION_REQUIREMENT"
            and superseded.get("runtime_execution_allowed") is False
        ),
        "execution_behavior_all_true": all(value is True for value in execution.values()),
        "required_outputs_all_true": all(value is True for value in outputs.values()),
        "fail_closed_rules_all_true": all(value is True for value in fail_closed.values()),
        "integration_finding_taxonomy_bound": set(data.get("allowed_integration_findings", [])) == EXPECTED_FINDINGS,
        "read_only_audit_execution_authorized": boundary.get("read_only_audit_execution_authorized") is True,
        "local_evidence_write_only": boundary.get("local_evidence_artifact_write_authorized") is True,
        "all_other_execution_boundaries_closed": all(
            value is False
            for key, value in boundary.items()
            if key not in {"read_only_audit_execution_authorized", "local_evidence_artifact_write_authorized"}
        ),
        "decision_bound": data.get("authorization_decision") == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_ARBITRATION_EVIDENCE_AUDIT",
        "next_decision_bound": data.get("next_decision") == "EXECUTE_AND_CERTIFY_READ_ONLY_METALS_FINAL_DECISION_ARBITRATION_EVIDENCE_AUDIT",
    }

    if not all(value is True for key, value in result.items() if key != "status"):
        result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
