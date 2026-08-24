from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "metals" / "tactical_policy_walk_forward_evaluation_design.json"


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("design_id") != "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-DESIGN-1":
        raise RuntimeError("unexpected walk-forward evaluation design")
    if contract.get("source_candidate_rule_design") != "METALS-TACTICAL-POLICY-CANDIDATE-RULE-DESIGN-1":
        raise RuntimeError("unexpected candidate-rule source")
    if contract.get("source_feasibility_audit") != "METALS-TACTICAL-POLICY-HISTORICAL-INPUT-FEASIBILITY-AUDIT-1":
        raise RuntimeError("unexpected feasibility-audit source")

    grid = contract["evaluation_grid"]
    if int(grid["walk_forward_step_observations"]) != 5:
        raise RuntimeError("walk-forward step changed")
    if list(grid["forward_horizons_observations"]) != [21, 63]:
        raise RuntimeError("forward horizons changed")
    if int(grid["forward_evaluable_grid_points_per_asset"]) != 88:
        raise RuntimeError("grid capacity changed")
    if int(grid["development_grid_points_per_asset"]) != 53:
        raise RuntimeError("development split changed")
    if int(grid["holdout_grid_points_per_asset"]) != 35:
        raise RuntimeError("holdout split changed")
    if int(grid["development_opportunity_grid_points"]) != 530:
        raise RuntimeError("development opportunity count changed")
    if int(grid["holdout_opportunity_grid_points"]) != 350:
        raise RuntimeError("holdout opportunity count changed")

    outcomes = contract["outcome_definitions"]
    if outcomes.get("all_outcomes_use_only_prices_strictly_after_the_decision_date") is not True:
        raise RuntimeError("future-only outcome separation is not required")

    rules = contract["interpretation_rules"]
    if rules.get("development_results_are_diagnostic_only") is not True:
        raise RuntimeError("development results are not diagnostic-only")
    if rules.get("candidate_rules_may_not_change_after_development_results_without_starting_a_new_validation_cycle") is not True:
        raise RuntimeError("candidate-rule lock after development is missing")
    if rules.get("holdout_results_are_final_for_this_candidate_version") is not True:
        raise RuntimeError("holdout finality is missing")
    if rules.get("overlapping_forward_windows_must_be_disclosed") is not True:
        raise RuntimeError("overlap disclosure is missing")
    if rules.get("duplicate_exposure_families_must_not_be_treated_as_independent_confirmation") is not True:
        raise RuntimeError("dependence disclosure is missing")

    pass_rules = contract["candidate_pass_fail_rules"]
    if int(pass_rules["minimum_supported_holdout_observations_per_compared_group"]) != 20:
        raise RuntimeError("minimum holdout group support changed")
    if pass_rules.get("if_minimum_group_support_not_met") != "INCONCLUSIVE_NOT_PASS":
        raise RuntimeError("insufficient-support handling changed")
    if pass_rules.get("passing_candidate_does_not_authorize_production_posture") is not True:
        raise RuntimeError("candidate pass improperly authorizes production posture")
    required = list(pass_rules["required_for_pass"])
    if len(required) != 5:
        raise RuntimeError("unexpected pass/fail requirement count")

    controls = contract["controls"]
    if controls.get("walk_forward_evaluation_design_authorized") is not True:
        raise RuntimeError("walk-forward evaluation design is not authorized")
    for key in (
        "forward_outcome_calculation_authorized",
        "historical_candidate_evaluation_authorized",
        "candidate_threshold_change_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited control changed unexpectedly: {key}")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": contract["design_id"],
        "source_candidate_rule_design": contract["source_candidate_rule_design"],
        "source_feasibility_audit": contract["source_feasibility_audit"],
        "eligible_vehicle_count": int(contract["eligible_vehicle_count"]),
        "reference_control_count": len(contract["reference_control_asset_ids"]),
        "walk_forward_step_observations": int(grid["walk_forward_step_observations"]),
        "forward_horizons_observations": list(grid["forward_horizons_observations"]),
        "development_grid_points_per_asset": int(grid["development_grid_points_per_asset"]),
        "holdout_grid_points_per_asset": int(grid["holdout_grid_points_per_asset"]),
        "development_opportunity_grid_points": int(grid["development_opportunity_grid_points"]),
        "holdout_opportunity_grid_points": int(grid["holdout_opportunity_grid_points"]),
        "development_results_diagnostic_only": True,
        "candidate_rules_locked_through_holdout": True,
        "overlapping_windows_disclosure_required": True,
        "minimum_supported_holdout_observations_per_compared_group": int(pass_rules["minimum_supported_holdout_observations_per_compared_group"]),
        "forward_outcome_calculation_authorized": False,
        "historical_candidate_evaluation_authorized": False,
        "tactical_posture_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
