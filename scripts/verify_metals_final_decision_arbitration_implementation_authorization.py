from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "final_decision_arbitration_with_forward_validation_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "final_decision_arbitration_implementation_authorization.json"

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
    "final_action_policy_json",
    "twelve_asset_final_action_matrix_json",
    "final_action_explanation_contract_json",
    "forward_validation_anchor_contract_json",
    "final_action_policy_summary_json",
}
EXPECTED_OPEN = {
    "final_action_policy_implementation_authorized",
    "forward_validation_anchor_implementation_authorized",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    design = load(DESIGN_PATH)
    auth = load(AUTH_PATH)
    boundary = auth["authorization_boundary"]
    open_boundaries = {key for key, value in boundary.items() if value is True}
    checks = {
        "read_only_inputs": True,
        "authorization_id_bound": auth["authorization_id"] == "METALS-FINAL-DECISION-ARBITRATION-IMPLEMENTATION-AUTHORIZATION-1",
        "source_design_bound": auth["source_design_id"] == design["design_id"],
        "source_head_bound": auth["source_design_head"] == "d52932bbc876da559b4565e6056b42302bbfe9a6",
        "database_sha_bound": auth["source_database_sha256"] == design["source_database_sha256"],
        "policy_label_bound": auth["policy_authority_label"] == design["arbitration_policy"]["policy_authority_label"],
        "twelve_asset_actions_exact": auth["authorized_current_asset_actions"] == EXPECTED_ACTIONS == design["current_asset_action_design"],
        "execution_behavior_all_true": len(auth["required_implementation_behavior"]) == 15 and all(value is True for value in auth["required_implementation_behavior"].values()),
        "required_outputs_exact": set(auth["required_outputs"].keys()) == EXPECTED_OUTPUTS,
        "required_outputs_all_true": all(value is True for value in auth["required_outputs"].values()),
        "design_outputs_match": set(auth["required_outputs"].keys()) == set(design["required_outputs_for_future_implementation"].keys()),
        "policy_implementation_authorized": boundary["final_action_policy_implementation_authorized"] is True,
        "forward_validation_anchor_implementation_authorized": boundary["forward_validation_anchor_implementation_authorized"] is True,
        "all_other_execution_boundaries_closed": len(boundary) == 15 and open_boundaries == EXPECTED_OPEN,
        "decision_bound": auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_DECISION_ARBITRATION_IMPLEMENTATION",
        "next_decision_bound": auth["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_METALS_FINAL_DECISION_ARBITRATION_IMPLEMENTATION",
    }
    checks["status"] = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps(checks, indent=2, sort_keys=True))
    if checks["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
