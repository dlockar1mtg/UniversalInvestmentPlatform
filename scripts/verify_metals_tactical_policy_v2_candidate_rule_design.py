from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_candidate_rule_design.json"


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    if contract.get("design_id") != "METALS-TACTICAL-POLICY-V2-CANDIDATE-RULE-DESIGN-1":
        raise RuntimeError("unexpected V2 candidate-rule design")
    if contract.get("source_research_design") != "METALS-TACTICAL-POLICY-V2-RESEARCH-DESIGN-1":
        raise RuntimeError("unexpected V2 research-design source")
    if contract.get("source_v1_candidate") != "METALS-TACTICAL-POLICY-CANDIDATE-RULE-DESIGN-1":
        raise RuntimeError("unexpected V1 candidate source")

    eligible = list(contract.get("eligible_vehicle_asset_ids") or [])
    reference = list(contract.get("reference_control_asset_ids") or [])
    postures = list(contract.get("candidate_postures") or [])
    inputs = list((contract.get("historical_validation_input_scope") or {}).get("required_price_derived_inputs") or [])
    rationale = contract.get("v2_change_rationale") or {}
    validation = contract.get("validation_requirements") or {}
    hard_gates = contract.get("hard_gates") or {}
    semantic = contract.get("semantic_constraints") or {}
    controls = contract.get("controls") or {}

    if len(eligible) != 10:
        raise RuntimeError("unexpected V2 eligible vehicle count")
    if reference != ["metals:vehicle:BIL"]:
        raise RuntimeError("BIL reference/control role changed")
    if sorted(postures) != sorted(["ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"]):
        raise RuntimeError("unexpected V2 posture vocabulary")
    if len(inputs) != 7:
        raise RuntimeError("unexpected V2 historical input count")

    if rationale.get("negative_signal_sensitivity_increased") is not True:
        raise RuntimeError("negative-signal sensitivity change not documented")
    if rationale.get("defensive_score_region_broadened_to_include_minus_one") is not True:
        raise RuntimeError("defensive score-region change not documented")
    if rationale.get("changes_use_consumed_v1_findings_as_research_only") is not True:
        raise RuntimeError("V1 research-only use not preserved")
    if rationale.get("no_new_unseen_validation_outcomes_used") is not True:
        raise RuntimeError("unseen outcome prohibition not preserved")

    if int(validation.get("minimum_compared_group_support", 0)) != 20:
        raise RuntimeError("minimum compared-group support changed")
    if list(validation.get("forward_horizons_observations") or []) != [21, 63]:
        raise RuntimeError("forward horizons changed")
    if int(validation.get("walk_forward_step_observations", 0)) != 5:
        raise RuntimeError("walk-forward step changed")
    if validation.get("defensive_63d_mean_maximum_adverse_excursion_must_be_more_negative_than_constructive") is not True:
        raise RuntimeError("corrected downside-validation direction missing")
    if float(validation.get("holdout_posture_change_rate_maximum", -1)) != 0.50:
        raise RuntimeError("holdout churn ceiling changed")
    if validation.get("new_validation_interval_must_be_disjoint_from_v1") is not True:
        raise RuntimeError("V2 disjoint validation requirement missing")
    if validation.get("candidate_rules_locked_before_new_validation_history_collection") is not True:
        raise RuntimeError("V2 rule lock before history collection missing")
    if validation.get("candidate_rules_locked_before_new_validation_outcome_inspection") is not True:
        raise RuntimeError("V2 rule lock before outcome inspection missing")

    if int(hard_gates.get("minimum_history_observations", 0)) != 252:
        raise RuntimeError("minimum history gate changed")
    if hard_gates.get("insufficient_current_authority_yields_no_tactical_posture") is not True:
        raise RuntimeError("missing-authority behavior changed")

    if semantic.get("defensive_signal_is_downside_warning") is not True:
        raise RuntimeError("defensive warning semantic missing")
    if semantic.get("more_negative_future_mae_is_evidence_consistent_with_defensive_warning") is not True:
        raise RuntimeError("corrected MAE semantic missing")
    if semantic.get("momentum_state_is_descriptive_not_predictive") is not True:
        raise RuntimeError("momentum semantic separation changed")

    if controls.get("v2_candidate_rule_design_authorized") is not True:
        raise RuntimeError("V2 candidate-rule design not authorized")
    for key in (
        "historical_expansion_feasibility_audit_authorized",
        "historical_expansion_execution_authorized",
        "new_validation_outcome_inspection_authorized",
        "historical_candidate_evaluation_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited control changed unexpectedly: {key}")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": contract["design_id"],
        "source_research_design": contract["source_research_design"],
        "source_v1_candidate": contract["source_v1_candidate"],
        "eligible_vehicle_count": len(eligible),
        "reference_control_count": len(reference),
        "historical_input_count": len(inputs),
        "candidate_postures": postures,
        "minimum_supported_observations_per_compared_group": int(validation["minimum_compared_group_support"]),
        "walk_forward_step_observations": int(validation["walk_forward_step_observations"]),
        "forward_horizons_observations": validation["forward_horizons_observations"],
        "negative_signal_sensitivity_increased": True,
        "defensive_score_region_broadened_to_include_minus_one": True,
        "corrected_downside_validation_direction_verified": True,
        "new_validation_interval_disjoint_required": True,
        "v2_rules_locked_before_new_history": True,
        "new_unseen_outcomes_used": False,
        "historical_expansion_feasibility_audit_authorized": False,
        "historical_expansion_execution_authorized": False,
        "new_validation_outcome_inspection_authorized": False,
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
