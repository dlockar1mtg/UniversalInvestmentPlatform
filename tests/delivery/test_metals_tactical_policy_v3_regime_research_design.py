from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARENT_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_research_design.json"
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_regime_research_design.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_regime_research_design.py"


def load_parent() -> dict[str, object]:
    return json.loads(PARENT_PATH.read_text(encoding="utf-8"))


def load_design() -> dict[str, object]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def test_regime_research_design_extends_certified_parent_without_reopening_v2() -> None:
    parent = load_parent()
    design = load_design()
    assert parent["design_id"] == "METALS-TACTICAL-POLICY-V3-RESEARCH-DESIGN-1"
    assert parent["next_decision"] == "AUTHORIZE_METALS_TACTICAL_POLICY_V3_REGIME_RESEARCH_DESIGN"
    assert design["design_id"] == "METALS-TACTICAL-POLICY-V3-REGIME-RESEARCH-DESIGN-1"
    assert design["source_v3_research_design"] == parent["design_id"]
    boundary = design["research_boundary"]
    assert boundary["consumed_v1_v2_evidence_may_be_used_for_research_and_development_only"] is True
    assert boundary["consumed_v1_v2_intervals_may_not_be_called_unseen_again"] is True
    assert boundary["new_validation_outcomes_may_not_be_inspected"] is True


def test_regime_families_preserve_required_semantics() -> None:
    regimes = load_design()["candidate_regime_families"]
    assert [item["regime_id"] for item in regimes] == [
        "TREND_PERSISTENCE",
        "MEAN_REVERSION_OR_EXHAUSTION",
        "NEUTRAL_OR_UNCERTAIN",
    ]
    assert regimes[0]["must_distinguish_trend_strength_from_persistence"] is True
    assert regimes[1]["must_not_infer_predictive_mean_reversion_from_v2_failure_alone"] is True
    assert regimes[2]["conflicting_evidence_must_be_allowed_to_resolve_to_neutral"] is True
    assert regimes[2]["insufficient_support_must_be_allowed_to_resolve_to_neutral"] is True
    assert regimes[2]["no_action_compatibility_required_for_later_policy_design"] is True


def test_candidate_inputs_are_point_in_time_and_declared_before_execution() -> None:
    inputs = load_design()["candidate_input_registry"]
    assert inputs["inputs_must_be_point_in_time"] is True
    assert inputs["future_returns_or_future_excursions_prohibited_as_classifier_inputs"] is True
    assert inputs["current_only_recommendation_or_risk_fields_prohibited_from_historical_backfill"] is True
    assert inputs["missing_historical_vintage_authority_must_remain_missing"] is True
    assert inputs["existing_inputs"] == [
        "return_1m_pct",
        "return_3m_pct",
        "return_6m_pct",
        "distance_ma50_pct",
        "distance_ma200_pct",
        "current_drawdown_pct",
        "realized_volatility_3m_pct",
    ]
    assert inputs["additional_candidate_inputs_to_define_before_execution"] == [
        "trend_slope",
        "return_dispersion",
        "volatility_change",
        "drawdown_recovery_rate",
        "distance_from_recent_extreme",
        "short_vs_long_momentum_spread",
    ]
    assert inputs["additional_candidate_inputs_are_research_candidates_not_final_authorized_features"] is True


def test_research_method_and_exposure_family_controls_are_fail_closed() -> None:
    design = load_design()
    method = design["research_method"]
    exposure = design["exposure_family_controls"]
    assert method["historical_study_role"] == "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE"
    assert method["classifier_inputs_must_be_frozen_before_historical_regime_study_execution"] is True
    assert method["candidate_regime_assignment_logic_must_be_versioned"] is True
    assert method["subsequent_outcomes_are_research_targets_not_classifier_inputs"] is True
    assert method["minimum_compared_group_support"] == 20
    assert method["minimum_compared_group_support_may_not_be_lowered_below_20"] is True
    assert method["no_regime_family_may_be_forced_when_evidence_is_conflicting"] is True
    assert exposure["bil_is_reference_control_only"] is True
    assert exposure["bil_may_not_be_treated_as_an_opportunity"] is True
    assert exposure["duplicate_exposure_families_are_not_independent_confirmation"] is True
    assert exposure["known_non_independent_groups"] == [["GLD", "IAU", "SGOL"], ["SIVR", "SLV"]]
    assert exposure["validation_may_not_count_duplicate_family_members_as_independent_confirmations"] is True


def test_regime_design_authorizes_design_only_not_execution_or_postures() -> None:
    controls = load_design()["controls"]
    assert controls["v3_research_design_authorized"] is True
    assert controls["v3_regime_research_design_authorized"] is True
    for key in (
        "v3_regime_definition_authorized",
        "v3_candidate_rule_design_authorized",
        "v3_historical_regime_research_execution_authorized",
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
    assert load_design()["next_decision"] == "AUTHORIZE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH"


def test_regime_research_verifier_is_static_and_does_not_calculate_market_outcomes() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    forbidden = (
        "yfinance",
        "yf.download(",
        ".history(",
        ".pct_change(",
        "forward_return",
        "maximum_adverse_excursion",
        "maximum_favorable_excursion",
        "duckdb.connect(",
    )
    for token in forbidden:
        assert token not in source
