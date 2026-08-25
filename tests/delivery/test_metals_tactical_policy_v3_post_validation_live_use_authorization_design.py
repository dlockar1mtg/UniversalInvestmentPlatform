from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization_design.json"
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_unseen_validation_result_review.json"


def load_design() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def load_review() -> dict:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def test_design_is_bound_to_certified_review_and_validation_pass() -> None:
    design = load_design()
    review = load_review()
    assert design["design_id"] == "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-DESIGN-1"
    assert design["source_review_id"] == "METALS-TACTICAL-POLICY-V3-UNSEEN-VALIDATION-RESULT-REVIEW-1"
    assert design["source_review_decision"] == "VALIDATION_PASS_CONFIRMED_FOR_POST_VALIDATION_LIVE_USE_CONSIDERATION"
    assert design["source_validation_result"] == "PASS"
    assert review["review_decision"] == design["source_review_decision"]
    assert review["controls"]["v3_unseen_validation_pass_certified"] is True
    assert review["controls"]["v3_tactical_policy_validated_for_live_use_consideration"] is True
    assert review["controls"]["live_tactical_posture_authorized"] is False


def test_validated_mapping_is_preserved_exactly() -> None:
    design = load_design()
    assert design["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1"
    assert design["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert design["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1"
    assert design["validated_mapping"] == {
        "TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE",
        "MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE",
        "NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY",
    }


def test_live_role_is_interpretive_not_trade_or_sizing_authority() -> None:
    role = load_design()["live_use_role_design"]
    assert role["role"] == "BOUNDED_METALS_TACTICAL_INTERPRETATION_OVERLAY"
    assert role["not_a_buy_signal"] is True
    assert role["not_a_sell_signal"] is True
    assert role["not_position_sizing"] is True
    assert role["not_portfolio_allocation"] is True
    assert role["not_expected_return_forecast"] is True
    assert role["not_long_term_thesis"] is True
    assert role["not_medium_term_opportunity_score"] is True
    assert role["not_risk_override"] is True


def test_interpretation_chain_and_non_override_rules_are_fixed() -> None:
    design = load_design()
    assert design["planned_uip_interpretation_chain"] == [
        "LONG_TERM_THESIS",
        "MEDIUM_TERM_OPPORTUNITY",
        "MOMENTUM_AND_REGIME",
        "TACTICAL_POSITION",
        "RISK_AND_DOWNSIDE",
        "WHY",
    ]
    rules = design["precedence_and_non_override_rules"]
    assert rules["long_term_thesis_remains_independent"] is True
    assert rules["medium_term_opportunity_remains_independent"] is True
    assert rules["risk_and_downside_remain_independent"] is True
    assert rules["tactical_overlay_may_not_convert_a_non_opportunity_into_an_opportunity_by_itself"] is True
    assert rules["tactical_overlay_may_not_suppress_or_hide_material_risk"] is True
    assert rules["neutral_state_may_not_be_forced_directional"] is True
    assert rules["duplicate_exposure_families_may_not_be_treated_as_independent_confirmation"] is True


def test_live_calculation_must_reuse_validated_point_in_time_policy() -> None:
    live = load_design()["live_calculation_design"]
    assert live["price_basis"] == "UNADJUSTED_CLOSE"
    assert live["required_current_price_field"] == "close_usd"
    assert live["classifier_rule_version_must_remain"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert live["action_mapping_version_must_remain"] == "METALS-V3-ACTION-MAPPING-1"
    assert live["point_in_time_only"] is True
    assert live["future_outcomes_may_not_enter_live_classification"] is True
    assert live["adaptive_thresholds_use_prior_observations_only"] is True
    assert live["same_locked_feature_formulas_as_validated_policy"] is True
    assert live["same_locked_assignment_order_as_validated_policy"] is True
    assert live["same_locked_action_mapping_as_validated_policy"] is True
    assert live["reference_control_bil_remains_non_opportunity"] is True


def test_freshness_provenance_and_fail_closed_boundaries_are_required() -> None:
    freshness = load_design()["freshness_and_fail_closed_design"]
    assert all(freshness.values())


def test_live_output_contract_contains_required_provenance_and_state_fields() -> None:
    output = load_design()["planned_live_output_contract"]
    required = set(output["required_fields"])
    assert {
        "asset_id", "ticker", "as_of_date", "candidate_regime", "tactical_state",
        "classifier_rule_version", "action_mapping_version", "price_semantics",
        "source_package_id", "state_available", "state_reason",
    }.issubset(required)
    assert output["raw_validation_outcomes_may_not_be_presented_as_current_forecasts"] is True
    assert output["historical_validation_statistics_may_be_used_only_as provenance_or_methodology_context"] is True


def test_presentation_semantics_do_not_become_trade_signals() -> None:
    presentation = load_design()["planned_presentation_semantics"]
    assert presentation["TACTICAL_SUPPORTIVE"] == "Supportive"
    assert presentation["TACTICAL_DEFENSIVE"] == "Defensive"
    assert presentation["NO_TACTICAL_OVERLAY"] == "Neutral / No Overlay"
    assert presentation["must_include_as_of_date"] is True
    assert presentation["must_include_methodology_or_rationale_linkage"] is True
    assert presentation["must_not_display_as_buy_hold_sell"] is True
    assert presentation["must_not_display_as_probability_of_gain"] is True
    assert presentation["must_not_display_as_position_size"] is True


def test_change_control_requires_new_version_and_new_unseen_validation() -> None:
    change = load_design()["change_control_design"]
    assert all(change.values())


def test_design_is_complete_but_no_downstream_authority_is_enabled() -> None:
    design = load_design()
    boundary = design["authorization_boundary"]
    assert boundary["design_complete"] is True
    for key, value in boundary.items():
        if key == "design_complete":
            continue
        assert value is False
    assert design["next_decision"] == "CONSIDER_METALS_TACTICAL_POLICY_V3_POST_VALIDATION_LIVE_USE_AUTHORIZATION"
