from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "final_decision_presentation_stage_authorization.json"

EXPECTED_OPEN = {
    "read_active_presentation_authorized",
    "reconstruct_certified_candidate_in_memory_authorized",
    "hosted_candidate_stage_authorized",
    "hosted_candidate_validate_staged_authorized",
    "candidate_rejection_on_stage_validation_failure_authorized",
    "local_stage_evidence_artifact_write_authorized",
}

EXPECTED_OUTPUTS = {
    "presentation_stage_plan_json",
    "hosted_stage_write_receipt_json",
    "staged_candidate_validation_json",
    "active_publication_preservation_json",
    "presentation_stage_summary_json",
}


def main() -> int:
    doc = json.loads(PATH.read_text(encoding="utf-8"))
    scope = doc["authorization_scope"]
    behavior = doc["required_stage_behavior"]
    outputs = doc["required_outputs"]

    open_scope = {key for key, value in scope.items() if value is True}
    result = {
        "status": "PASS",
        "authorization_id_bound": doc["authorization_id"] == "METALS-FINAL-DECISION-PRESENTATION-STAGE-AUTHORIZATION-1",
        "source_design_bound": doc["source_integration_design_id"] == "METALS-FINAL-DECISION-PRESENTATION-INTEGRATION-DESIGN-1",
        "source_rehearsal_bound": doc["source_projection_rehearsal_id"] == "METALS-FINAL-DECISION-PRESENTATION-PROJECTION-REHEARSAL-1",
        "source_head_bound": doc["source_projection_rehearsal_governed_head"] == "1bf46d889f478fc0614467b503300a04fecfff8a",
        "database_sha_bound": doc["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "active_publication_bound": doc["source_active_publication_id"] == "metals-v3-commodity-explanation-r4-20260826" and doc["source_active_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5" and doc["source_active_publication_record_count"] == 12477,
        "candidate_bound": doc["certified_candidate_publication_id"] == "metals-final-decision-presentation-r1-20260827" and doc["certified_candidate_content_fingerprint"] == "9de5edb450542be85dd68f3b0dd539dc520ef1f92b9de1b743672d7a6b1e289d" and doc["certified_candidate_record_count"] == 12477,
        "rehearsal_counts_bound": doc["certified_target_payload_mutation_count"] == 12 and doc["certified_recommendation_value_change_count"] == 9 and doc["certified_recommendation_value_retain_count"] == 3 and doc["certified_non_target_record_count"] == 12465 and doc["certified_non_target_canonical_mismatch_count"] == 0,
        "open_scope_exact": open_scope == EXPECTED_OPEN,
        "activation_closed": scope["hosted_activation_authorized"] is False,
        "active_mutation_closed": scope["active_publication_mutation_authorized"] is False,
        "downstream_writes_closed": all(scope[key] is False for key in (
            "analytical_database_write_authorized",
            "non_presentation_hosted_database_write_authorized",
            "runtime_change_authorized",
            "recommendation_recompute_authorized",
            "forecast_refresh_authorized",
            "model_refresh_authorized",
            "network_collection_authorized",
            "pr_authorized",
            "main_deploy_authorized",
            "allocation_or_execution_authorized",
        )),
        "required_behavior_all_true": len(behavior) == 24 and all(value is True for value in behavior.values()),
        "required_outputs_exact": set(outputs) == EXPECTED_OUTPUTS,
        "required_outputs_all_true": all(value is True for value in outputs.values()),
        "decision_bound": doc["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_DECISION_PRESENTATION_STAGE",
        "next_decision_bound": doc["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_METALS_FINAL_DECISION_PRESENTATION_STAGE",
    }

    if not all(value is True for key, value in result.items() if key != "status"):
        result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
