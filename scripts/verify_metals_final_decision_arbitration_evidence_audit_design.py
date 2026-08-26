from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "final_decision_arbitration_evidence_audit_design.json"

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

counts = data["certified_semantic_audit_counts"]
superseded = data["superseded_runtime_authorization"]
requirement = data["final_decision_requirement"]
facts = data["documented_pipeline_facts"]
boundaries = data["boundaries"]

checks = {
    "design_id_bound": data["design_id"] == "METALS-FINAL-DECISION-ARBITRATION-EVIDENCE-AUDIT-DESIGN-1",
    "source_head_bound": data["source_governed_head"] == "9a4f009cc7d4080b4ff142c8c67793bd31b51768",
    "database_sha_bound": data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
    "hosted_r4_bound": data["active_hosted_publication_id"] == "metals-v3-commodity-explanation-r4-20260826" and data["active_hosted_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5" and int(data["active_hosted_record_count"]) == 12477,
    "semantic_audit_bound": data["source_semantic_audit_id"] == "METALS-DECISION-SEMANTICS-AUDIT-EXECUTION-1",
    "audit_counts_bound": counts == {
        "asset_count": 12,
        "safe_primary_status_count": 5,
        "blocked_primary_status_count": 7,
        "raw_adjusted_sign_conflict_count": 8,
        "contradiction_count": 17,
    },
    "asset_scope_exact": set(data["required_asset_scope"]) == expected_assets,
    "superseded_authorization_bound": superseded["authorization_id"] == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-IMPLEMENTATION-AUTHORIZATION-1" and superseded["head"] == "9a4f009cc7d4080b4ff142c8c67793bd31b51768",
    "superseded_runtime_execution_prohibited": superseded["state"] == "SUPERSEDED_BY_FINAL_DECISION_REQUIREMENT" and superseded["runtime_execution_allowed"] is False,
    "one_final_action_required": requirement["one_final_uip_action_per_investable_asset"] is True and requirement["internal_conflict_must_not_be_final_action"] is True,
    "final_action_validation_required": requirement["final_action_must_be_evidence_based"] is True and requirement["final_action_must_be_explainable"] is True and requirement["final_action_must_be_backtestable_before_production_activation"] is True and requirement["final_action_must_not_be_invented_from_unvalidated_thresholds"] is True,
    "pipeline_facts_all_true": bool(facts) and all(value is True for value in facts.values()),
    "audit_questions_all_true": bool(data["required_audit_questions"]) and all(value is True for value in data["required_audit_questions"].values()),
    "required_outputs_all_true": bool(data["required_outputs"]) and all(value is True for value in data["required_outputs"].values()),
    "fail_closed_rules_all_true": bool(data["fail_closed_rules"]) and all(value is True for value in data["fail_closed_rules"].values()),
    "integration_finding_taxonomy_bound": set(data["allowed_integration_findings"]) == {"LEGITIMATE_SEPARATION", "PIPELINE_BYPASS", "STALE_AUTHORITY", "CALIBRATION_DEFECT", "MULTIPLE_CONTRIBUTING_CAUSES", "UNRESOLVED"},
    "all_execution_boundaries_closed": bool(boundaries) and all(value is False for value in boundaries.values()),
    "decision_bound": data["design_decision"] == "APPROVE_METALS_FINAL_DECISION_ARBITRATION_EVIDENCE_AUDIT_DESIGN_FOR_READ_ONLY_EXECUTION_AUTHORIZATION_CONSIDERATION",
    "next_decision_bound": data["next_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_ARBITRATION_EVIDENCE_AUDIT",
}

result = {
    "status": "PASS" if all(checks.values()) else "FAIL",
    "read_only": True,
    **checks,
}
print(json.dumps(result, indent=2, sort_keys=True))
if result["status"] != "PASS":
    raise SystemExit(1)
