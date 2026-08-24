from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_research_design.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_research_design.py"


def load_design() -> dict[str, object]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_v3_research_design_preserves_failed_v2_evidence() -> None:
    design = load_design()
    evidence = design["preserved_evidence"]
    assert design["design_id"] == "METALS-TACTICAL-POLICY-V3-RESEARCH-DESIGN-1"
    assert design["source_v2_failed_validation_review"] == "METALS-TACTICAL-POLICY-V2-FAILED-VALIDATION-REVIEW-1"
    assert evidence["v1_result"] == "INCONCLUSIVE"
    assert evidence["v2_result"] == "FAIL"
    assert evidence["v2_failure_support_limited"] is False
    assert evidence["v2_directional_check_failures"] == 3
    assert evidence["v2_constructive_63d_observations"] == 489
    assert evidence["v2_defensive_63d_observations"] == 639
    assert evidence["v2_validation_interval_consumed"] is True
    assert evidence["v2_live_use_authorized"] is False


def test_v3_requires_regime_aware_architecture_without_authorizing_actions() -> None:
    design = load_design()
    architecture = design["v3_architecture_direction"]
    assert architecture["regime_aware_framework_required"] is True
    assert architecture["single_unconditional_constructive_defensive_mapping_prohibited"] is True
    assert architecture["candidate_regime_families"] == [
        "TREND_PERSISTENCE",
        "MEAN_REVERSION_OR_EXHAUSTION",
        "NEUTRAL_OR_UNCERTAIN",
    ]
    assert architecture["regime_classifier_must_be_separate_from_action_mapping"] is True
    assert architecture["regime_classifier_must_use_point_in_time_inputs_only"] is True
    assert architecture["regime_classifier_may_not_use_future_returns_or_future_excursions"] is True
    assert architecture["neutral_or_uncertain_regime_must_allow_no_action"] is True
    assert architecture["candidate_postures_may_not_be_assigned_until_separately_authorized"] is True


def test_consumed_intervals_remain_consumed_and_new_validation_is_required() -> None:
    methods = load_design()["research_method_requirements"]
    assert methods["v1_and_v2_consumed_outcomes_may_be_used_for_research_hypothesis_generation"] is True
    assert methods["v1_or_v2_consumed_intervals_may_not_be_called_unseen_again"] is True
    assert methods["v3_regime_definition_must_be_locked_before_any_new_unseen_validation_outcomes_are_inspected"] is True
    assert methods["v3_action_mapping_must_be_locked_before_any_new_unseen_validation_outcomes_are_inspected"] is True
    assert methods["new_unseen_validation_authority_required_before_live_use"] is True
    assert methods["minimum_compared_group_support_may_not_be_lowered_below_20"] == 20


def test_v3_design_does_not_pre_authorize_downstream_execution() -> None:
    controls = load_design()["controls"]
    assert controls["v3_research_design_authorized"] is True
    for key in (
        "v3_regime_definition_authorized",
        "v3_candidate_rule_design_authorized",
        "v3_historical_research_execution_authorized",
        "new_validation_data_collection_authorized",
        "new_validation_outcome_inspection_authorized",
        "historical_candidate_evaluation_authorized",
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
        assert controls[key] is False


def test_verifier_is_static_and_does_not_calculate_market_outcomes() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    forbidden = (
        "yfinance",
        "yf.download(",
        ".history(",
        ".pct_change(",
        "forward_return",
        "maximum_adverse_excursion",
        "maximum_favorable_excursion",
    )
    for token in forbidden:
        assert token not in source
