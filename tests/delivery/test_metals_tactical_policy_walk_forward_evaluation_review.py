from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "tactical_policy_walk_forward_evaluation_review.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_walk_forward_evaluation_review.py"


def load_review() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_review_files_exist() -> None:
    assert CONTRACT.is_file()
    assert VERIFIER.is_file()


def test_candidate_v1_is_certified_inconclusive_not_authorized() -> None:
    review = load_review()
    assert review["review_status"] == "INCONCLUSIVE_NOT_AUTHORIZED"
    controls = review["controls"]
    assert controls["candidate_v1_inconclusive_certified"] is True
    assert controls["candidate_v1_pass_authorized"] is False
    assert controls["candidate_v1_fail_authorized"] is False
    assert controls["tactical_posture_authorized"] is False


def test_minimum_support_failure_is_preserved() -> None:
    observed = load_review()["observed_holdout"]
    assert observed["constructive_observation_count"] == 280
    assert observed["defensive_observation_count"] == 15
    assert observed["minimum_supported_observations_per_compared_group"] == 20
    assert observed["minimum_group_support_met"] is False


def test_directional_separation_is_not_promoted_to_validation() -> None:
    review = load_review()
    observed = review["observed_holdout"]
    findings = review["review_findings"]
    assert observed["constructive_63d_median_return_pct"] > observed["defensive_63d_median_return_pct"]
    assert observed["constructive_63d_positive_return_rate"] > observed["defensive_63d_positive_return_rate"]
    assert findings["constructive_vs_defensive_return_separation_is_directionally_favorable_but_not_validated"] is True
    assert findings["constructive_vs_defensive_positive_rate_separation_is_directionally_favorable_but_not_validated"] is True


def test_mae_semantics_and_holdout_consumption_are_locked() -> None:
    review = load_review()
    observed = review["observed_holdout"]
    findings = review["review_findings"]
    constraints = review["required_next_cycle_constraints"]
    assert observed["defensive_63d_mean_maximum_adverse_excursion_pct"] < observed["constructive_63d_mean_maximum_adverse_excursion_pct"]
    assert findings["original_mae_pass_rule_is_semantically_misaligned_with_a_defensive_risk_signal"] is True
    assert findings["observed_holdout_results_are_now_consumed_and_may_not_be_reused_as_unseen_validation_for_a_revised_candidate"] is True
    assert constraints["new_unseen_validation_evidence_required_for_production_authorization"] is True


def test_no_production_authority_is_created() -> None:
    controls = load_review()["controls"]
    for key in (
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
        assert controls[key] is False
