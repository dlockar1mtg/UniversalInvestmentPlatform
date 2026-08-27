from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "final_decision_presentation_integration_design.json"

EXPECTED_ACTIONS = {
    "metals:commodity:gold": "HOLD",
    "metals:commodity:uranium": "HOLD",
    "metals:vehicle:BIL": "REFERENCE_CONTROL",
    "metals:vehicle:COPX": "HOLD",
    "metals:vehicle:CPER": "HOLD",
    "metals:vehicle:GLD": "WATCH",
    "metals:vehicle:IAU": "WATCH",
    "metals:vehicle:PPLT": "WATCH",
    "metals:vehicle:SGOL": "WATCH",
    "metals:vehicle:SIVR": "WATCH",
    "metals:vehicle:SLV": "WATCH",
    "metals:vehicle:URA": "HOLD",
}

EXPECTED_OUTPUTS = {
    "presentation_projection_plan_json",
    "twelve_target_payload_delta_json",
    "non_target_preservation_summary_json",
    "candidate_publication_manifest_json",
    "candidate_publication_validation_json",
    "rehearsal_summary_json",
}


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    strategy = design["integration_strategy"]
    semantics = design["recommendation_payload_semantics"]
    invariants = design["required_projection_invariants"]
    boundaries = design["boundaries"]

    checks = {
        "read_only": True,
        "design_id_bound": design["design_id"] == "METALS-FINAL-DECISION-PRESENTATION-INTEGRATION-DESIGN-1",
        "source_head_bound": design["source_governed_head"] == "b621c661f9e1e2976e0c69b565a4b8e179a9aeac",
        "source_policy_bound": design["source_policy_implementation_id"] == "METALS-FINAL-DECISION-ARBITRATION-IMPLEMENTATION-1",
        "database_sha_bound": design["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "active_publication_bound": design["source_active_publication_id"] == "metals-v3-commodity-explanation-r4-20260826" and design["source_active_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5" and int(design["source_active_publication_record_count"]) == 12477,
        "twelve_actions_exact": design["certified_final_actions"] == EXPECTED_ACTIONS,
        "clone_strategy_bound": strategy["source_publication_strategy"] == "CLONE_CURRENT_ACTIVE_PUBLICATION_AND_MUTATE_ONLY_THE_TWELVE_MAPPED_METALS_RECOMMENDATION_PAYLOADS",
        "record_count_preserved": int(strategy["expected_total_record_count_after_projection"]) == 12477,
        "read_api_change_not_required": strategy["read_api_change_required"] is False,
        "in_place_mutation_prohibited": strategy["active_publication_mutation"] is False,
        "recommendation_becomes_final_action": semantics["recommendation_field_becomes_final_user_facing_action"] is True,
        "native_recommendation_preserved": semantics["native_recommendation_field_preserves_pre_integration_recommendation"] is True,
        "final_action_added": semantics["final_action_field_added"] is True,
        "policy_label_bound": design["policy_authority_label"] == "POLICY_DRIVEN_PENDING_FORWARD_EMPIRICAL_VALIDATION",
        "projection_invariants_all_true": all(value is True for value in invariants.values()),
        "required_outputs_exact": set(design["required_outputs_for_future_rehearsal"].keys()) == EXPECTED_OUTPUTS,
        "required_outputs_all_true": all(value is True for value in design["required_outputs_for_future_rehearsal"].values()),
        "all_execution_boundaries_closed": all(value is False for value in boundaries.values()),
        "decision_bound": design["design_decision"] == "APPROVE_METALS_FINAL_DECISION_PRESENTATION_INTEGRATION_DESIGN_FOR_REHEARSAL_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": design["next_decision"] == "AUTHORIZE_READ_ONLY_METALS_FINAL_DECISION_PRESENTATION_PROJECTION_REHEARSAL",
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, **checks}, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
