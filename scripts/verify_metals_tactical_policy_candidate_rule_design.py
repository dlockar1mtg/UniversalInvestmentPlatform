from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_candidate_rule_design.json"


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    if contract.get("design_id") != "METALS-TACTICAL-POLICY-CANDIDATE-RULE-DESIGN-1":
        raise RuntimeError("unexpected tactical candidate rule design")
    if contract.get("source_validation_design") != "METALS-TACTICAL-POLICY-VALIDATION-DESIGN-1":
        raise RuntimeError("unexpected tactical validation-design authority")

    eligible = list(contract.get("eligible_vehicle_asset_ids") or [])
    reference = list(contract.get("reference_control_asset_ids") or [])
    postures = sorted(str(item) for item in contract.get("candidate_postures") or [])

    if len(eligible) != 10 or len(set(eligible)) != 10:
        raise RuntimeError("eligible vehicle population must contain exactly 10 unique vehicles")
    if reference != ["metals:vehicle:BIL"]:
        raise RuntimeError("BIL must remain the sole reference/control asset")
    if "metals:vehicle:BIL" in eligible:
        raise RuntimeError("BIL may not enter the tactical opportunity set")
    if postures != sorted(["ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"]):
        raise RuntimeError("candidate posture vocabulary changed")

    history_scope = contract.get("historical_validation_input_scope") or {}
    if history_scope.get("time_aligned_price_derived_inputs_only") is not True:
        raise RuntimeError("historical evaluation must use time-aligned price-derived inputs only")
    if history_scope.get("current_only_recommendation_or_risk_may_not_be_backfilled_into_history") is not True:
        raise RuntimeError("current-only recommendation/risk backfill prohibition changed")
    if history_scope.get("missing_historical_vintage_authority_must_remain_missing") is not True:
        raise RuntimeError("missing historical authority preservation changed")

    required_inputs = set(history_scope.get("required_price_derived_inputs") or [])
    expected_inputs = {
        "return_1m_pct",
        "return_3m_pct",
        "return_6m_pct",
        "distance_ma50_pct",
        "distance_ma200_pct",
        "current_drawdown_pct",
        "realized_volatility_3m_pct",
    }
    if required_inputs != expected_inputs:
        raise RuntimeError("historical candidate input vocabulary changed")

    rules = contract.get("candidate_signal_rules") or {}
    expected_rule_keys = {
        "return_1m",
        "return_3m",
        "return_6m",
        "distance_ma50",
        "distance_ma200",
        "drawdown_penalty",
        "volatility_penalty",
    }
    if set(rules) != expected_rule_keys:
        raise RuntimeError("candidate signal-rule set changed")

    mapping = contract.get("candidate_score_mapping") or {}
    if set(mapping) != {"ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"}:
        raise RuntimeError("candidate score mapping is incomplete")
    if mapping["ACCUMULATE"].get("minimum_score") != 5:
        raise RuntimeError("ACCUMULATE threshold changed")
    if mapping["AVOID"].get("maximum_score") != -5:
        raise RuntimeError("AVOID threshold changed")

    gates = contract.get("hard_gates") or {}
    if gates.get("reference_control_receives_no_opportunity_posture") is not True:
        raise RuntimeError("reference/control posture gate changed")
    if int(gates.get("minimum_history_observations", 0)) != 252:
        raise RuntimeError("minimum history gate changed")
    if gates.get("all_required_price_derived_inputs_must_be_available") is not True:
        raise RuntimeError("required historical input availability gate changed")
    if gates.get("current_application_requires_current_price_authority") is not True:
        raise RuntimeError("current-price authority gate changed")
    if gates.get("current_application_requires_recommendation_and_risk_authority") is not True:
        raise RuntimeError("recommendation/risk authority gate changed")
    if gates.get("insufficient_current_authority_yields_no_tactical_posture") is not True:
        raise RuntimeError("insufficient-authority behavior changed")

    validation = contract.get("validation_plan") or {}
    if int(validation.get("walk_forward_step_observations", 0)) != 5:
        raise RuntimeError("walk-forward step changed")
    if list(validation.get("forward_horizons_observations") or []) != [21, 63]:
        raise RuntimeError("forward evaluation horizons changed")
    for key in (
        "development_then_holdout_required",
        "candidate_rules_locked_before_forward_outcome_evaluation",
        "measure_return_distribution_by_posture",
        "measure_downside_and_drawdown_by_posture",
        "measure_turnover_and_posture_churn",
        "compare_buy_and_hold_baseline",
        "compare_no_tactical_overlay_baseline",
        "production_threshold_changes_require_new_validation_cycle",
    ):
        if validation.get(key) is not True:
            raise RuntimeError(f"required candidate validation control changed: {key}")

    semantics = contract.get("semantic_constraints") or {}
    for key in (
        "momentum_state_is_descriptive_not_predictive",
        "candidate_policy_is_not_yet_authorized_advice",
        "forecast_validation_separate_from_policy_validation",
        "cross_domain_rank_prohibited",
        "universal_allocation_policy_prohibited",
        "automatic_execution_prohibited",
    ):
        if semantics.get(key) is not True:
            raise RuntimeError(f"candidate semantic constraint changed: {key}")

    controls = contract.get("controls") or {}
    if controls.get("candidate_rule_design_authorized") is not True:
        raise RuntimeError("candidate rule design is not authorized")
    for key in (
        "historical_candidate_evaluation_authorized",
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
            raise RuntimeError(f"prohibited candidate-rule control changed: {key}")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": contract["design_id"],
        "source_validation_design": contract["source_validation_design"],
        "eligible_vehicle_count": len(eligible),
        "reference_control_count": len(reference),
        "bil_reference_control_verified": reference == ["metals:vehicle:BIL"],
        "candidate_postures": postures,
        "historical_input_count": len(required_inputs),
        "historical_inputs_time_aligned_only": True,
        "current_only_evidence_backfill_prohibited": True,
        "minimum_history_observations": int(gates["minimum_history_observations"]),
        "walk_forward_step_observations": int(validation["walk_forward_step_observations"]),
        "forward_horizons_observations": list(validation["forward_horizons_observations"]),
        "thresholds_pre_specified": True,
        "development_then_holdout_required": True,
        "tactical_posture_authorized": False,
        "historical_candidate_evaluation_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
