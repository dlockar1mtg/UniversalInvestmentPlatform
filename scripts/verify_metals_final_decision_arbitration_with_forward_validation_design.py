from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "final_decision_arbitration_with_forward_validation_design.json"


def main() -> None:
    design = json.loads(PATH.read_text(encoding="utf-8"))

    expected_actions = {
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

    expected_outputs = {
        "final_action_policy_json",
        "twelve_asset_final_action_matrix_json",
        "final_action_explanation_contract_json",
        "forward_validation_anchor_contract_json",
        "final_action_policy_summary_json",
    }

    checks = {
        "read_only": True,
        "design_id_bound": design.get("design_id") == "METALS-FINAL-DECISION-ARBITRATION-WITH-FORWARD-VALIDATION-DESIGN-1",
        "source_head_bound": design.get("source_governed_head") == "6463c704a7fe1c0b71aeec3a12e73877628b506e",
        "database_sha_bound": design.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "limited_history_bound": design.get("source_limited_historical_evidence_assessment_id") == "METALS-NATIVE-URANIUM-LIMITED-HISTORICAL-EVIDENCE-ASSESSMENT-1",
        "limited_policy_authority_bound": design.get("source_policy_authority") == "INSUFFICIENT_FOR_UNIVERSAL_POLICY_CERTIFICATION",
        "taxonomy_excludes_decision_conflict": "DECISION_CONFLICT" not in design.get("final_action_taxonomy", []),
        "twelve_asset_actions_exact": design.get("current_asset_action_design") == expected_actions,
        "bullish_conflicts_capped_at_watch": all(design.get("current_asset_action_design", {}).get(asset) == "WATCH" for asset in ["metals:vehicle:GLD", "metals:vehicle:IAU", "metals:vehicle:PPLT", "metals:vehicle:SGOL", "metals:vehicle:SIVR", "metals:vehicle:SLV"]),
        "bil_reference_only": design.get("current_asset_action_design", {}).get("metals:vehicle:BIL") == "REFERENCE_CONTROL",
        "policy_label_bound": design.get("arbitration_policy", {}).get("policy_authority_label") == "POLICY_DRIVEN_PENDING_FORWARD_EMPIRICAL_VALIDATION",
        "no_new_numeric_thresholds": design.get("governance_principles", {}).get("no_new_numeric_thresholds_created") is True,
        "forward_validation_required": design.get("governance_principles", {}).get("forward_validation_required_for_independent_sample_growth") is True,
        "forward_validation_contract_all_true": all(value is True for value in design.get("forward_validation_contract", {}).values()),
        "required_outputs_exact": set(design.get("required_outputs_for_future_implementation", {}).keys()) == expected_outputs,
        "required_outputs_all_true": all(value is True for value in design.get("required_outputs_for_future_implementation", {}).values()),
        "fail_closed_all_true": all(value is True for value in design.get("fail_closed_rules", {}).values()),
        "all_execution_boundaries_closed": all(value is False for value in design.get("boundaries", {}).values()),
        "decision_bound": design.get("design_decision") == "APPROVE_METALS_FINAL_DECISION_ARBITRATION_WITH_FORWARD_VALIDATION_DESIGN_FOR_IMPLEMENTATION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": design.get("next_decision") == "AUTHORIZE_BOUNDED_METALS_FINAL_DECISION_ARBITRATION_IMPLEMENTATION",
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, **checks}, indent=2, sort_keys=True))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
