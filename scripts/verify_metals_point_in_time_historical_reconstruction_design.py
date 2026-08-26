from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "point_in_time_historical_reconstruction_design.json"

EXPECTED_CUTOFFS = [
    "2024-12-31",
    "2025-01-31",
    "2025-02-28",
    "2025-03-31",
    "2025-04-30",
    "2025-05-31",
    "2025-06-30",
    "2025-07-31",
]

EXPECTED_OUTPUTS = {
    "reconstructed_forecast_rows_json",
    "reconstructed_forecast_rows_csv",
    "cutoff_input_lineage_json",
    "point_in_time_invariant_checks_json",
    "reconstruction_coverage_json",
    "unavailable_cutoff_register_json",
    "reconstruction_summary_json",
}


def main() -> int:
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    checks = {
        "read_only": True,
        "design_id_bound": design.get("design_id") == "METALS-POINT-IN-TIME-HISTORICAL-RECONSTRUCTION-DESIGN-1",
        "source_head_bound": design.get("source_governed_head") == "8e1f9f47029ec6790094fdfac991e2fe8df7e00a",
        "feasibility_bound": design.get("source_feasibility_finding") == "HOSTED_POINT_IN_TIME_RECONSTRUCTION_FEASIBLE_FOR_BOUNDED_12_MONTH_URANIUM_COHORT",
        "hosted_counts_bound": (
            design.get("certified_feasibility_findings", {}).get("hosted_benchmark_series_count") == 9
            and design.get("certified_feasibility_findings", {}).get("hosted_benchmark_row_count") == 18
            and design.get("certified_feasibility_findings", {}).get("hosted_vehicle_series_count") == 11
            and design.get("certified_feasibility_findings", {}).get("hosted_vehicle_row_count") == 8426
        ),
        "backfill_counts_bound": (
            design.get("certified_feasibility_findings", {}).get("benchmark_backfilled_row_count") == 18
            and design.get("certified_feasibility_findings", {}).get("vehicle_backfilled_row_count") == 8316
        ),
        "usable_cutoffs_bound": design.get("reconstruction_scope", {}).get("candidate_cutoffs") == EXPECTED_CUTOFFS,
        "mature_horizon_bound": design.get("reconstruction_scope", {}).get("authorized_design_horizons_months") == [12],
        "uranium_cohort_bound": design.get("reconstruction_scope", {}).get("benchmark_cohort") == ["METALS:COMMODITY:URANIUM"],
        "bil_reference_only_bound": design.get("reconstruction_scope", {}).get("bil_role") == "REFERENCE_CONTROL_ONLY",
        "pit_rules_all_true": all(design.get("required_point_in_time_rules", {}).values()) and len(design.get("required_point_in_time_rules", {})) == 16,
        "outcome_constraints_all_true": all(design.get("historical_outcome_constraints", {}).values()) and len(design.get("historical_outcome_constraints", {})) == 6,
        "required_outputs_exact": set(design.get("required_outputs_for_future_execution", {})) == EXPECTED_OUTPUTS,
        "required_outputs_all_true": all(design.get("required_outputs_for_future_execution", {}).values()),
        "all_execution_boundaries_closed": all(value is False for value in design.get("boundaries", {}).values()),
        "decision_bound": design.get("design_decision") == "APPROVE_METALS_POINT_IN_TIME_HISTORICAL_RECONSTRUCTION_DESIGN_FOR_EXECUTION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": design.get("next_decision") == "AUTHORIZE_READ_ONLY_METALS_POINT_IN_TIME_HISTORICAL_RECONSTRUCTION",
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, **checks}, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
