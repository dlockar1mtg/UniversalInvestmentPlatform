from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_freeze.json"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_authorization.json"


def main() -> int:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))

    if freeze.get("freeze_id") != "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1":
        raise RuntimeError("unexpected freeze id")
    if freeze.get("source_authorization") != auth.get("authorization_id"):
        raise RuntimeError("authorization source mismatch")
    if freeze.get("research_role") != "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE":
        raise RuntimeError("research role changed")

    price = freeze.get("price_basis") or {}
    if price.get("required_price_field") != "UNADJUSTED_CLOSE":
        raise RuntimeError("price basis changed")
    if int(price.get("minimum_history_before_candidate_label", -1)) != 452:
        raise RuntimeError("minimum history changed")

    thresholds = freeze.get("point_in_time_adaptive_thresholds") or {}
    if thresholds.get("threshold_history_uses_only_values_available_through_t_minus_1") is not True:
        raise RuntimeError("point-in-time threshold guard missing")
    if thresholds.get("percentiles_are_computed_per_vehicle") is not True:
        raise RuntimeError("per-vehicle threshold guard missing")

    logic = freeze.get("candidate_regime_assignment_logic") or {}
    if logic.get("logic_version") != "METALS-V3-REGIME-CANDIDATE-RULES-1":
        raise RuntimeError("unexpected candidate rules version")
    expected_order = ["ELIGIBILITY_GATE", "TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION", "NEUTRAL_OR_UNCERTAIN"]
    if logic.get("assignment_order") != expected_order:
        raise RuntimeError("assignment order changed")
    if logic.get("action_mapping", {}).get("authorized") is not False:
        raise RuntimeError("action mapping unexpectedly authorized")

    outcome = freeze.get("research_outcome_protocol") or {}
    for key in (
        "candidate_labels_must_be_materialized_before_outcome_columns_are_calculated_or_joined",
        "label_ledger_hash_must_be_recorded_before_outcome_comparison",
        "future_returns_and_excursions_are_research_targets_only",
        "overlapping_forward_windows_must_be_disclosed",
        "results_must_be_labelled_development_evidence_not_unseen_validation",
        "no_threshold_or_rule_may_be_changed_after_label_ledger_materialization_without_new_version_and_new_governance_decision",
    ):
        if outcome.get(key) is not True:
            raise RuntimeError(f"outcome protocol guard missing: {key}")

    support = freeze.get("support_and_exposure_family_controls") or {}
    if int(support.get("minimum_compared_group_support", -1)) != 20:
        raise RuntimeError("minimum support floor changed")
    if support.get("bil_is_reference_control_only") is not True:
        raise RuntimeError("BIL control guard changed")
    if support.get("known_non_independent_groups") != [["GLD", "IAU", "SGOL"], ["SIVR", "SLV"]]:
        raise RuntimeError("non-independent group registry changed")

    controls = freeze.get("controls") or {}
    if controls.get("candidate_input_definition_frozen") is not True:
        raise RuntimeError("candidate inputs not frozen")
    if controls.get("candidate_regime_assignment_logic_frozen") is not True:
        raise RuntimeError("candidate rules not frozen")
    if controls.get("v3_historical_regime_research_execution_authorized") is not True:
        raise RuntimeError("historical regime research execution not authorized")
    for key in (
        "historical_outcome_inspection_executed",
        "v3_regime_definition_authorized",
        "v3_candidate_rule_design_authorized",
        "new_validation_outcome_inspection_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "native_source_query_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited control changed: {key}")

    if freeze.get("next_decision") != "EXECUTE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH_USING_FROZEN_RULES":
        raise RuntimeError("unexpected next decision")

    result = {
        "status": "PASS",
        "read_only": True,
        "freeze_id": freeze["freeze_id"],
        "source_authorization": freeze["source_authorization"],
        "research_role": freeze["research_role"],
        "required_price_field": price["required_price_field"],
        "minimum_history_before_candidate_label": price["minimum_history_before_candidate_label"],
        "candidate_regime_family_count": 3,
        "candidate_input_definition_frozen": controls["candidate_input_definition_frozen"],
        "candidate_regime_assignment_logic_frozen": controls["candidate_regime_assignment_logic_frozen"],
        "historical_outcome_inspection_executed": controls["historical_outcome_inspection_executed"],
        "minimum_support_floor": support["minimum_compared_group_support"],
        "bil_reference_control_only": support["bil_is_reference_control_only"],
        "known_non_independent_group_count": len(support["known_non_independent_groups"]),
        "regime_definition_authorized": controls["v3_regime_definition_authorized"],
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": controls["cross_domain_rank_authorized"],
        "allocation_policy_authorized": controls["allocation_policy_authorized"],
        "automatic_execution_authorized": controls["automatic_execution_authorized"],
        "next_decision": freeze["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
