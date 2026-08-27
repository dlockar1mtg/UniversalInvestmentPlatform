from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "final_decision_presentation_activation_authorization.json"

data = json.loads(PATH.read_text(encoding="utf-8"))

expected_open = {
    "read_current_active_publication_authorized",
    "read_staged_candidate_authorized",
    "validate_staged_candidate_pre_activation_authorized",
    "activate_exact_certified_candidate_authorized",
    "read_post_activation_state_authorized",
    "local_activation_evidence_artifact_write_authorized",
}

scope = data["authorization_scope"]
open_scope = {k for k, v in scope.items() if v is True}

expected_outputs = {
    "presentation_activation_plan_json",
    "pre_activation_validation_json",
    "hosted_activation_receipt_json",
    "post_activation_validation_json",
    "previous_publication_supersession_json",
    "presentation_activation_summary_json",
}

checks = {
    "authorization_id_bound": data["authorization_id"] == "METALS-FINAL-DECISION-PRESENTATION-ACTIVATION-AUTHORIZATION-1",
    "source_stage_authorization_bound": data["source_stage_authorization_id"] == "METALS-FINAL-DECISION-PRESENTATION-STAGE-AUTHORIZATION-1",
    "source_stage_head_bound": data["source_stage_governed_head"] == "96dac900d0a4a6d57e8f90741162aa777e0adfa9",
    "source_stage_execution_bound": data["source_stage_execution_id"] == "METALS-FINAL-DECISION-PRESENTATION-STAGE-1",
    "database_sha_bound": data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
    "current_active_bound": (
        data["expected_current_active_publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
        and data["expected_current_active_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
        and data["expected_current_active_publication_record_count"] == 12477
    ),
    "candidate_bound": (
        data["authorized_candidate_publication_id"] == "metals-final-decision-presentation-r1-20260827"
        and data["authorized_candidate_pre_activation_status"] == "STAGED"
        and data["authorized_candidate_content_fingerprint"] == "9de5edb450542be85dd68f3b0dd539dc520ef1f92b9de1b743672d7a6b1e289d"
        and data["authorized_candidate_record_count"] == 12477
        and data["authorized_target_payload_count"] == 12
    ),
    "final_action_counts_bound": data["authorized_final_action_counts"] == {"HOLD": 5, "WATCH": 6, "REFERENCE_CONTROL": 1},
    "open_scope_exact": open_scope == expected_open,
    "other_activation_closed": scope["activate_any_other_publication_authorized"] is False,
    "rollback_closed": scope["manual_rollback_authorized"] is False,
    "downstream_writes_closed": all(
        scope[key] is False
        for key in (
            "analytical_database_write_authorized",
            "non_presentation_hosted_database_write_authorized",
            "runtime_code_change_authorized",
            "recommendation_recompute_authorized",
            "forecast_refresh_authorized",
            "model_refresh_authorized",
            "network_collection_authorized",
            "pr_authorized",
            "main_deploy_authorized",
            "allocation_or_execution_authorized",
        )
    ),
    "required_behavior_all_true": all(data["required_activation_behavior"].values()),
    "required_outputs_exact": set(data["required_outputs"]) == expected_outputs,
    "required_outputs_all_true": all(data["required_outputs"].values()),
    "decision_bound": data["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_DECISION_PRESENTATION_ACTIVATION",
    "next_decision_bound": data["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_METALS_FINAL_DECISION_PRESENTATION_ACTIVATION",
}

result = {"status": "PASS" if all(checks.values()) else "FAIL", **checks}
print(json.dumps(result, indent=2, sort_keys=True))

if result["status"] != "PASS":
    raise SystemExit(1)
