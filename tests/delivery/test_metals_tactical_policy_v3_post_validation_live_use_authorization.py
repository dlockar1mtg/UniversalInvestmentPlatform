from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization.json"
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_post_validation_live_use_authorization_design.json"
REVIEW_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_unseen_validation_result_review.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_authorization_is_bound_to_certified_design_review_and_pass() -> None:
    auth = load_json(AUTH_PATH)
    design = load_json(DESIGN_PATH)
    review = load_json(REVIEW_PATH)
    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-1"
    assert auth["source_design_id"] == design["design_id"] == "METALS-TACTICAL-POLICY-V3-POST-VALIDATION-LIVE-USE-AUTHORIZATION-DESIGN-1"
    assert auth["source_review_id"] == review["review_id"] == "METALS-TACTICAL-POLICY-V3-UNSEEN-VALIDATION-RESULT-REVIEW-1"
    assert auth["source_validation_result"] == "PASS"
    assert review["review_decision"] == "VALIDATION_PASS_CONFIRMED_FOR_POST_VALIDATION_LIVE_USE_CONSIDERATION"
    assert review["controls"]["v3_unseen_validation_pass_certified"] is True
    assert review["controls"]["v3_tactical_policy_validated_for_live_use_consideration"] is True


def test_validated_classifier_and_mapping_are_preserved_exactly() -> None:
    auth = load_json(AUTH_PATH)
    assert auth["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1"
    assert auth["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert auth["source_action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1"
    assert auth["authorized_mapping"] == {
        "TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE",
        "MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE",
        "NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY",
    }


def test_bounded_live_tactical_interpretation_is_authorized() -> None:
    auth = load_json(AUTH_PATH)
    assert auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_V3_LIVE_TACTICAL_INTERPRETATION"
    live = auth["authorized_live_use"]
    assert live["role"] == "BOUNDED_METALS_TACTICAL_INTERPRETATION_OVERLAY"
    assert live["current_state_materialization_authorized"] is True
    assert live["candidate_tactical_posture_authorized"] is True
    assert live["live_tactical_posture_authorized"] is True
    assert live["point_in_time_only"] is True
    assert live["price_basis"] == "UNADJUSTED_CLOSE"
    assert live["required_current_price_field"] == "close_usd"
    assert live["latest_certified_available_market_observation_required"] is True
    assert live["future_outcomes_may_not_enter_live_classification"] is True
    assert live["same_locked_feature_formulas_as_validated_policy"] is True
    assert live["same_locked_assignment_order_as_validated_policy"] is True
    assert live["same_locked_action_mapping_as_validated_policy"] is True
    assert live["reference_control_bil_remains_non_opportunity"] is True


def test_authorized_overlay_remains_interpretive_only() -> None:
    limits = load_json(AUTH_PATH)["interpretation_limits"]
    assert set(limits) == {
        "not_a_buy_signal",
        "not_a_sell_signal",
        "not_position_sizing",
        "not_portfolio_allocation",
        "not_expected_return_forecast",
        "not_long_term_thesis",
        "not_medium_term_opportunity_score",
        "not_risk_override",
        "tactical_overlay_may_not_convert_a_non_opportunity_into_an_opportunity_by_itself",
        "tactical_overlay_may_not_suppress_or_hide_material_risk",
        "neutral_state_may_not_be_forced_directional",
    }
    assert all(limits.values())


def test_live_output_contract_is_provenanced_and_bounded() -> None:
    output = load_json(AUTH_PATH)["live_output_contract"]
    assert {
        "asset_id", "ticker", "as_of_date", "candidate_regime", "tactical_state",
        "classifier_rule_version", "action_mapping_version", "price_semantics",
        "source_package_id", "state_available", "state_reason",
    }.issubset(set(output["required_fields"]))
    assert output["state_labels"] == {
        "TACTICAL_SUPPORTIVE": "Supportive",
        "TACTICAL_DEFENSIVE": "Defensive",
        "NO_TACTICAL_OVERLAY": "Neutral / No Overlay",
    }
    assert output["raw_validation_outcomes_may_not_be_presented_as_current_forecasts"] is True
    assert output["historical_validation_statistics_may_be_used_only_as_provenance_or_methodology_context"] is True


def test_freshness_fail_closed_and_change_control_are_exact() -> None:
    auth = load_json(AUTH_PATH)
    freshness = auth["freshness_and_fail_closed_controls"]
    assert all(freshness.values())
    change = auth["change_control"]
    assert set(change) == {
        "validated_classifier_and_mapping_are_immutable_for_v3_live_use",
        "any_classifier_formula_change_requires_new_policy_version",
        "any_threshold_logic_change_requires_new_policy_version",
        "any_action_mapping_change_requires_new_policy_version",
        "any_new_policy_version_requires_new_unseen_validation_before_live_use",
        "consumed_v1_v2_and_v3_validation_intervals_may_not_be_reused_as_unseen_evidence",
    }
    assert all(change.values())


def test_downstream_authorities_remain_off() -> None:
    auth = load_json(AUTH_PATH)
    downstream = auth["downstream_authorization_boundary"]
    assert set(downstream) == {
        "production_database_write_authorized",
        "presentation_activation_authorized",
        "native_source_query_authorized",
        "network_collection_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    }
    assert not any(downstream.values())
    assert auth["next_decision"] == "IMPLEMENT_METALS_TACTICAL_POLICY_V3_CURRENT_STATE_MATERIALIZATION"
