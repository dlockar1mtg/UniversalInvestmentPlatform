from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "point_in_time_historical_reconstruction_execution_authorization.json"
DESIGN = ROOT / "config" / "metals" / "point_in_time_historical_reconstruction_design.json"

EXPECTED_OUTPUTS = {
    "reconstructed_forecast_rows_json",
    "reconstructed_forecast_rows_csv",
    "cutoff_input_lineage_json",
    "point_in_time_invariant_checks_json",
    "reconstruction_coverage_json",
    "unavailable_cutoff_register_json",
    "reconstruction_summary_json",
}

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


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    auth = load(AUTH)
    design = load(DESIGN)
    scope = auth.get("authorized_scope", {})
    behavior = auth.get("required_execution_behavior", {})
    outputs = auth.get("required_outputs", {})
    boundary = auth.get("authorization_boundary", {})

    allowed_true = {
        "point_in_time_reconstruction_execution_authorized",
        "hosted_read_only_access_authorized",
        "local_evidence_artifact_write_authorized",
    }

    checks = {
        "read_only_inputs": True,
        "authorization_id_bound": auth.get("authorization_id") == "METALS-POINT-IN-TIME-HISTORICAL-RECONSTRUCTION-EXECUTION-AUTHORIZATION-1",
        "source_design_bound": auth.get("source_design_id") == design.get("design_id") == "METALS-POINT-IN-TIME-HISTORICAL-RECONSTRUCTION-DESIGN-1",
        "source_head_bound": auth.get("source_design_head") == "c03eb42e42a295fcbcf9155c6e3fd5aee8c54987",
        "database_sha_bound": auth.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "cutoffs_bound": scope.get("candidate_cutoffs") == EXPECTED_CUTOFFS,
        "horizon_bound": scope.get("horizons_months") == [12],
        "uranium_cohort_bound": scope.get("benchmark_cohort") == ["METALS:COMMODITY:URANIUM"],
        "vehicle_context_bound": scope.get("vehicle_context_series_count") == 11,
        "bil_reference_only_bound": scope.get("bil_role") == "REFERENCE_CONTROL_ONLY",
        "execution_behavior_all_true": len(behavior) == 16 and all(value is True for value in behavior.values()),
        "required_outputs_exact": set(outputs) == EXPECTED_OUTPUTS,
        "required_outputs_all_true": len(outputs) == 7 and all(value is True for value in outputs.values()),
        "reconstruction_authorized": boundary.get("point_in_time_reconstruction_execution_authorized") is True,
        "hosted_read_only_authorized": boundary.get("hosted_read_only_access_authorized") is True,
        "local_evidence_write_authorized": boundary.get("local_evidence_artifact_write_authorized") is True,
        "all_other_execution_boundaries_closed": all(value is False for key, value in boundary.items() if key not in allowed_true),
        "design_outputs_match": set(design.get("required_outputs_for_future_execution", {})) == EXPECTED_OUTPUTS,
        "decision_bound": auth.get("authorization_decision") == "AUTHORIZE_READ_ONLY_METALS_POINT_IN_TIME_HISTORICAL_RECONSTRUCTION",
        "next_decision_bound": auth.get("next_decision") == "EXECUTE_AND_CERTIFY_METALS_POINT_IN_TIME_HISTORICAL_RECONSTRUCTION",
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, **checks}, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
