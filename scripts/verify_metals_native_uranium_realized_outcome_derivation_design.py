from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "native_uranium_realized_outcome_derivation_design.json"


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    expected_outputs = {
        "native_uranium_realized_outcome_event_json",
        "forecast_state_outcome_alignment_csv",
        "forecast_state_outcome_alignment_json",
        "native_outcome_lineage_json",
        "independence_accounting_json",
        "derivation_invariant_checks_json",
        "derivation_summary_json",
    }

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id_bound": design.get("design_id") == "METALS-NATIVE-URANIUM-REALIZED-OUTCOME-DERIVATION-DESIGN-1",
        "source_head_bound": design.get("source_governed_head") == "8dc0f86c2278c41e2a8dae9430fe5271245869d6",
        "source_reconstruction_bound": design.get("source_reconstruction_id") == "METALS-POINT-IN-TIME-HISTORICAL-RECONSTRUCTION-1",
        "alignment_finding_bound": design.get("source_alignment_finding") == "ALL_8_RECONSTRUCTED_FORECAST_STATES_SHARE_NATIVE_AS_OF_2024_12_31_AND_MATCH_NATIVE_URANIUM_CURRENT_VALUE_EXACTLY",
        "forecast_states_bound": design.get("certified_alignment_findings", {}).get("reconstructed_forecast_state_count") == 8,
        "native_as_of_bound": design.get("certified_alignment_findings", {}).get("unique_reconstructed_as_of_date") == "2024-12-31",
        "native_authority_bound": design.get("certified_alignment_findings", {}).get("native_uranium_observation_dates") == ["2024-12-31", "2025-12-31"],
        "current_value_alignment_bound": design.get("certified_alignment_findings", {}).get("forecast_current_value_native_authority_match_count") == 8,
        "forecast_anchor_bound": design.get("outcome_semantics", {}).get("forecast_horizon_anchor") == "RECONSTRUCTED_NATIVE_AS_OF_DATE",
        "target_date_bound": design.get("outcome_semantics", {}).get("target_outcome_date") == "2025-12-31",
        "formula_bound": design.get("outcome_semantics", {}).get("realized_return_formula") == "future_native_value / as_of_native_value - 1",
        "independence_bound": design.get("independence_and_counting_rules", {}).get("distinct_native_outcome_event_count") == 1 and design.get("independence_and_counting_rules", {}).get("effective_independent_outcome_n_must_equal_one") is True,
        "derivation_rules_all_true": all(design.get("required_derivation_rules", {}).values()),
        "required_outputs_exact": set(design.get("required_outputs_for_future_execution", {}).keys()) == expected_outputs,
        "required_outputs_all_true": all(design.get("required_outputs_for_future_execution", {}).values()),
        "all_execution_boundaries_closed": all(value is False for value in design.get("boundaries", {}).values()),
        "decision_bound": design.get("design_decision") == "APPROVE_BOUNDED_NATIVE_URANIUM_REALIZED_OUTCOME_DERIVATION_DESIGN_FOR_EXECUTION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": design.get("next_decision") == "AUTHORIZE_BOUNDED_NATIVE_URANIUM_REALIZED_OUTCOME_DERIVATION",
    }

    if not all(value is True for key, value in result.items() if key != "status"):
        result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
