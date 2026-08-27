from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "final_decision_presentation_integration_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "final_decision_presentation_projection_rehearsal_authorization.json"


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    expected_open = {
        "read_active_presentation_authorized",
        "local_in_memory_projection_authorized",
        "local_evidence_artifact_write_authorized",
    }
    observed_open = {k for k, v in auth["authorization_scope"].items() if v is True}
    expected_outputs = {
        "presentation_projection_plan_json",
        "twelve_target_payload_delta_json",
        "non_target_preservation_summary_json",
        "candidate_publication_manifest_json",
        "candidate_publication_validation_json",
        "rehearsal_summary_json",
    }

    checks = {
        "read_only_scope": observed_open == expected_open,
        "authorization_id_bound": auth.get("authorization_id") == "METALS-FINAL-DECISION-PRESENTATION-PROJECTION-REHEARSAL-AUTHORIZATION-1",
        "source_design_bound": auth.get("source_design_id") == design.get("design_id"),
        "source_head_bound": auth.get("source_design_head") == "71062dbee559ea21389f2408867dc921aafd3475",
        "database_sha_bound": auth.get("source_database_sha256") == design.get("source_database_sha256"),
        "active_publication_bound": (
            auth.get("source_active_publication_id") == design.get("source_active_publication_id")
            and auth.get("source_active_publication_fingerprint") == design.get("source_active_publication_fingerprint")
            and auth.get("source_active_publication_record_count") == design.get("source_active_publication_record_count")
        ),
        "required_behavior_all_true": all(auth["required_rehearsal_behavior"].values()),
        "required_outputs_exact": set(auth["required_outputs"]) == expected_outputs,
        "required_outputs_all_true": all(auth["required_outputs"].values()),
        "hosted_stage_closed": auth["authorization_scope"].get("hosted_stage_authorized") is False,
        "hosted_activation_closed": auth["authorization_scope"].get("hosted_activation_authorized") is False,
        "all_downstream_writes_closed": all(
            auth["authorization_scope"].get(key) is False
            for key in (
                "active_publication_mutation_authorized",
                "analytical_database_write_authorized",
                "hosted_database_write_authorized",
                "runtime_change_authorized",
                "recommendation_recompute_authorized",
                "forecast_refresh_authorized",
                "model_refresh_authorized",
                "network_collection_authorized",
                "pr_authorized",
                "main_deploy_authorized",
                "allocation_or_execution_authorized",
            )
        ),
        "decision_bound": auth.get("authorization_decision") == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_PRESENTATION_PROJECTION_REHEARSAL",
        "next_decision_bound": auth.get("next_decision") == "EXECUTE_AND_CERTIFY_READ_ONLY_METALS_FINAL_DECISION_PRESENTATION_PROJECTION_REHEARSAL",
    }
    result = {**checks, "status": "PASS" if all(checks.values()) else "FAIL"}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
