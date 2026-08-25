from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_regime_definition_lock_decision.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))

    require(decision.get("decision_id") == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-LOCK-DECISION-1", "unexpected decision id")
    require(decision.get("source_review_id") == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-REVIEW-1", "unexpected source review")
    require(decision.get("source_execution_id") == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-EXECUTION-1", "unexpected source execution")
    require(decision.get("source_freeze_id") == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1", "unexpected source freeze")
    require(decision.get("source_rule_version") == "METALS-V3-REGIME-CANDIDATE-RULES-1", "unexpected rule version")
    require(decision.get("source_label_ledger_sha256") == "41f00a74c8116c59b5e36dc039db43a2481ffce9f1ce663da00c270d8c483dfd", "unexpected label ledger sha")
    require(decision.get("source_review_status") == "SUFFICIENT_FOR_REGIME_DEFINITION_LOCK_CONSIDERATION", "unexpected review status")
    require(decision.get("decision") == "LOCK_METALS_TACTICAL_POLICY_V3_REGIME_DEFINITION", "unexpected decision")

    rationale = decision.get("decision_rationale") or {}
    require(rationale.get("directional_support_gate_met") is True, "support gate not met")
    require(rationale.get("directional_exposure_family_gate_met") is True, "exposure family gate not met")
    require(rationale.get("directional_return_separation_consistent_across_21d_63d_126d") is True, "directional separation not consistent")
    require(rationale.get("neutral_or_uncertain_is_fail_closed_default") is True, "neutral fail-closed control changed")
    require(int(rationale.get("trend_persistence_observation_count", -1)) == 550, "trend persistence support changed")
    require(int(rationale.get("mean_reversion_or_exhaustion_observation_count", -1)) == 368, "mean reversion support changed")
    require(int(rationale.get("neutral_or_uncertain_observation_count", -1)) == 3902, "neutral support changed")
    require(int(rationale.get("each_candidate_regime_exposure_family_count", -1)) == 7, "exposure family count changed")
    require(rationale.get("development_evidence_not_unseen_validation") is True, "development boundary changed")
    require(rationale.get("observation_counts_are_not_independent_sample_counts") is True, "overlap disclosure changed")
    require(rationale.get("duplicate_exposure_families_are_not_independent_confirmation") is True, "duplicate exposure control changed")

    locked = decision.get("locked_regime_definition") or {}
    require(locked.get("definition_id") == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1", "unexpected definition id")
    require(locked.get("classifier_rule_version") == "METALS-V3-REGIME-CANDIDATE-RULES-1", "classifier version changed")
    require(locked.get("classifier_definition_source") == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1", "classifier source changed")
    require(locked.get("candidate_regime_families") == ["TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION", "NEUTRAL_OR_UNCERTAIN"], "candidate regime families changed")
    for key in (
        "candidate_input_definitions_locked_to_freeze",
        "adaptive_threshold_definitions_locked_to_freeze",
        "candidate_regime_assignment_logic_locked_to_freeze",
        "neutral_or_uncertain_remains_fail_closed_default",
        "future_returns_or_excursions_may_not_be_classifier_inputs",
        "current_only_recommendation_or_risk_fields_may_not_be_backfilled_historically",
        "missing_historical_vintage_authority_must_remain_missing",
    ):
        require(locked.get(key) is True, f"locked definition control changed: {key}")

    scope = decision.get("scope_of_lock") or {}
    require(scope.get("regime_definition_authorized") is True, "regime definition not authorized")
    require(scope.get("regime_definition_locked") is True, "regime definition not locked")
    require(scope.get("classifier_definition_may_be_used_as_input_to_separately_governed_action_mapping_design") is True, "action mapping design input not authorized")
    for key in (
        "action_mapping_authorized",
        "candidate_tactical_posture_authorized",
        "live_tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "native_source_query_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        require(scope.get(key) is False, f"prohibited authority changed: {key}")

    validation = decision.get("validation_boundary") or {}
    for key in (
        "development_evidence_may_support_classifier_lock",
        "development_evidence_is_not_unseen_validation",
        "v1_v2_intervals_remain_consumed",
        "new_unseen_validation_authority_required_before_live_tactical_use",
        "locked_classifier_may_not_be_changed_after_new_unseen_validation_outcomes_are_inspected_without_new_version_and_governance_decision",
        "future_action_mapping_must_be_frozen_before_new_unseen_validation_outcomes_are_inspected",
    ):
        require(validation.get(key) is True, f"validation boundary changed: {key}")

    require(decision.get("next_decision") == "DESIGN_METALS_TACTICAL_POLICY_V3_ACTION_MAPPING", "unexpected next decision")

    result = {
        "status": "PASS",
        "read_only": True,
        "decision_id": decision["decision_id"],
        "source_review_id": decision["source_review_id"],
        "source_label_ledger_sha256": decision["source_label_ledger_sha256"],
        "definition_id": locked["definition_id"],
        "classifier_rule_version": locked["classifier_rule_version"],
        "candidate_regime_family_count": len(locked["candidate_regime_families"]),
        "regime_definition_authorized": scope["regime_definition_authorized"],
        "regime_definition_locked": scope["regime_definition_locked"],
        "action_mapping_authorized": scope["action_mapping_authorized"],
        "tactical_posture_authorized": scope["live_tactical_posture_authorized"],
        "new_unseen_validation_required_before_live_use": validation["new_unseen_validation_authority_required_before_live_tactical_use"],
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "model_retraining_executed": False,
        "next_decision": decision["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
