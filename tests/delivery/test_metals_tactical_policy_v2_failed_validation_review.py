from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_failed_validation_review.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v2_failed_validation_review.py"


def load_review() -> dict[str, object]:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def test_review_preserves_failed_result_and_consumed_interval() -> None:
    review = load_review()
    assert review["evaluation_result"] == "FAIL"
    assert review["validation_interval"]["consumed"] is True
    assert review["review_findings"]["v2_failure_is_conclusive_under_locked_rules"] is True
    assert review["review_findings"]["consumed_validation_interval_may_not_be_reused_as_unseen_evidence"] is True


def test_review_preserves_support_and_directional_failures() -> None:
    review = load_review()
    support = review["observed_support"]
    assert support["constructive_63d_observations"] == 489
    assert support["defensive_63d_observations"] == 639
    assert support["minimum_required_per_compared_group"] == 20
    assert support["support_requirement_met"] is True
    checks = review["governed_check_results"]
    assert checks["constructive_63d_median_return_gt_defensive"] is False
    assert checks["constructive_63d_positive_return_rate_gt_defensive"] is False
    assert checks["defensive_63d_mean_mae_more_negative_than_constructive"] is False
    assert checks["holdout_posture_change_rate_lte_0_50"] is True


def test_review_prohibits_live_use_and_retesting_consumed_interval() -> None:
    review = load_review()
    controls = review["controls"]
    assert controls["v2_candidate_live_use_authorized"] is False
    assert controls["candidate_rule_change_authorized"] is False
    assert controls["candidate_threshold_change_authorized"] is False
    assert controls["consumed_interval_reuse_as_unseen_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["automatic_execution_authorized"] is False


def test_review_points_to_new_v3_research_cycle_only() -> None:
    review = load_review()
    assert review["controls"]["v3_research_design_authorized"] is False
    assert review["next_decision"] == "AUTHORIZE_METALS_TACTICAL_POLICY_V3_RESEARCH_DESIGN"


def test_verifier_is_static_and_does_not_recalculate_outcomes() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    prohibited = (
        "pct_change(",
        ".rolling(",
        "forward_return_",
        "mae_63d",
        "mfe_63d",
        "yfinance",
        "yf.download(",
    )
    for token in prohibited:
        assert token not in source
