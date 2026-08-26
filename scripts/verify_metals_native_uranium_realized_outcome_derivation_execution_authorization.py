from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "native_uranium_realized_outcome_derivation_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "native_uranium_realized_outcome_derivation_execution_authorization.json"

EXPECTED_OUTPUTS = {
    "native_uranium_realized_outcome_event_json",
    "forecast_state_outcome_alignment_csv",
    "forecast_state_outcome_alignment_json",
    "native_outcome_lineage_json",
    "independence_accounting_json",
    "derivation_invariant_checks_json",
    "derivation_summary_json",
}


def main() -> None:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    boundary = auth["authorization_boundary"]
    open_boundaries = {k for k, v in boundary.items() if v is True}
    expected_open = {
        "native_uranium_realized_outcome_derivation_authorized",
        "hosted_read_only_access_authorized",
        "local_evidence_artifact_write_authorized",
    }

    result = {
        "status": "PASS",
        "read_only_inputs": True,
        "authorization_id_bound": auth["authorization_id"] == "METALS-NATIVE-URANIUM-REALIZED-OUTCOME-DERIVATION-EXECUTION-AUTHORIZATION-1",
        "source_design_bound": auth["source_design_id"] == design["design_id"],
        "source_head_bound": auth["source_design_head"] == "7e80a189f2731c2d11e22a0fa1d75a82226c9264",
        "source_reconstruction_bound": auth["source_reconstruction_id"] == design["source_reconstruction_id"],
        "database_sha_bound": auth["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "scope_bound": auth["authorized_outcome_scope"]["forecast_state_count"] == 8 and auth["authorized_outcome_scope"]["distinct_native_outcome_event_count"] == 1 and auth["authorized_outcome_scope"]["effective_independent_outcome_n"] == 1,
        "native_as_of_bound": auth["authorized_outcome_scope"]["native_as_of_date"] == "2024-12-31",
        "target_date_bound": auth["authorized_outcome_scope"]["target_outcome_date"] == "2025-12-31",
        "formula_bound": auth["authorized_outcome_scope"]["realized_return_formula"] == "future_native_value / as_of_native_value - 1",
        "execution_behavior_all_true": len(auth["required_execution_behavior"]) == 16 and all(auth["required_execution_behavior"].values()),
        "required_outputs_exact": set(auth["required_outputs"]) == EXPECTED_OUTPUTS and set(design["required_outputs_for_future_execution"]) == EXPECTED_OUTPUTS,
        "required_outputs_all_true": all(auth["required_outputs"].values()),
        "derivation_authorized": boundary["native_uranium_realized_outcome_derivation_authorized"] is True,
        "hosted_read_only_authorized": boundary["hosted_read_only_access_authorized"] is True,
        "local_evidence_write_authorized": boundary["local_evidence_artifact_write_authorized"] is True,
        "all_other_execution_boundaries_closed": len(boundary) == 17 and open_boundaries == expected_open,
        "design_outputs_match": set(auth["required_outputs"]) == set(design["required_outputs_for_future_execution"]),
        "decision_bound": auth["authorization_decision"] == "AUTHORIZE_BOUNDED_NATIVE_URANIUM_REALIZED_OUTCOME_DERIVATION",
        "next_decision_bound": auth["next_decision"] == "EXECUTE_AND_CERTIFY_BOUNDED_NATIVE_URANIUM_REALIZED_OUTCOME_DERIVATION",
    }

    result["status"] = "PASS" if all(v is True for k, v in result.items() if k != "status") else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
