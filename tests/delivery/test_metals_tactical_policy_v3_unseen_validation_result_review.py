from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_unseen_validation_result_review.json"


def load_review() -> dict:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def test_review_identity_and_sources_are_fixed() -> None:
    review = load_review()
    assert review["review_id"] == "METALS-TACTICAL-POLICY-V3-UNSEEN-VALIDATION-RESULT-REVIEW-1"
    assert review["source_execution_id"] == "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-OUTCOME-INSPECTION-1"
    assert review["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1"
    assert review["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert review["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1"
    assert review["source_unseen_package_id"] == "metals-v3-new-unseen-validation-20230822-20260824"


def test_review_binds_exact_execution_artifact_hashes() -> None:
    hashes = load_review()["source_execution_artifacts"]
    assert hashes == {
        "label_ledger_sha256": "1f543a8a4b570a042289a098fc8e4cae06b3c43a553fd7c1000bb6a50bed4ae9",
        "outcome_ledger_sha256": "f687cf33d41d4235a1bd735b3c79fdf22fa7b0ce01c16e8c36c3714ac097e429",
        "validation_result_sha256": "a4e0d27aa3e994f92570e6fccf7e88edde0f205da647ddd2d8a6d970173de663",
        "execution_manifest_sha256": "aa698df5e191f91504608644e8be2f568f8f6f57c13b56a836c5d24311221965",
    }


def test_governed_validation_pass_is_preserved() -> None:
    governed = load_review()["governed_validation_result"]
    assert governed["validation_result"] == "PASS"
    assert governed["primary_horizon_trading_days"] == 63
    assert governed["primary_support_gate_met"] is True
    assert governed["primary_exposure_family_gate_met"] is True
    assert governed["all_three_primary_directional_checks_met"] is True
    assert governed["supportive_63d_observation_count"] == 801
    assert governed["defensive_63d_observation_count"] == 1152
    assert governed["supportive_63d_exposure_family_count"] == 7
    assert governed["defensive_63d_exposure_family_count"] == 7
    assert governed["minimum_compared_group_support"] == 20
    assert governed["minimum_distinct_exposure_families_per_directional_state"] == 2
    assert governed["secondary_horizons_cannot_substitute_for_primary_failure"] is True


def test_review_findings_confirm_unseen_validation_without_live_authority() -> None:
    findings = load_review()["review_findings"]
    assert findings["genuinely_unseen_validation_completed"] is True
    assert findings["locked_classifier_was_used"] is True
    assert findings["frozen_action_mapping_was_used"] is True
    assert findings["label_ledger_was_hashed_before_forward_outcome_calculation"] is True
    assert findings["consumed_v2_history_was_used_only_for_point_in_time_warmup"] is True
    assert findings["consumed_v2_rows_entered_new_validation_labels_or_outcomes"] is False
    assert findings["primary_validation_support_was_sufficient"] is True
    assert findings["primary_validation_exposure_family_breadth_was_sufficient"] is True
    assert findings["all_three_locked_primary_directional_checks_passed"] is True
    assert findings["v3_tactical_policy_cleared_unseen_validation"] is True
    assert findings["validation_pass_does_not_itself_authorize_live_tactical_posture"] is True
    assert findings["classifier_or_mapping_may_not_be_retuned_on_consumed_unseen_interval"] is True
    assert findings["unseen_interval_is_consumed_for_future_validation"] is True


def test_review_decision_and_controls_are_fail_closed() -> None:
    review = load_review()
    assert review["review_decision"] == "VALIDATION_PASS_CONFIRMED_FOR_POST_VALIDATION_LIVE_USE_CONSIDERATION"
    controls = review["controls"]
    assert controls["v3_unseen_validation_pass_certified"] is True
    assert controls["v3_tactical_policy_validated_for_live_use_consideration"] is True
    assert controls["candidate_tactical_posture_authorized"] is False
    assert controls["live_tactical_posture_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["native_source_query_authorized"] is False
    assert controls["forecast_refresh_authorized"] is False
    assert controls["model_retraining_authorized"] is False
    assert controls["cross_domain_rank_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False
    assert review["next_decision"] == "DESIGN_METALS_TACTICAL_POLICY_V3_POST_VALIDATION_LIVE_USE_AUTHORIZATION"
