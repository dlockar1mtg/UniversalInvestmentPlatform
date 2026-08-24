from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FREEZE_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_freeze.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_historical_regime_research_freeze.py"


def load_freeze() -> dict[str, object]:
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


def test_freeze_preserves_development_only_boundary() -> None:
    freeze = load_freeze()
    assert freeze["freeze_id"] == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1"
    assert freeze["research_role"] == "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE"
    assert freeze["price_basis"]["required_price_field"] == "UNADJUSTED_CLOSE"
    assert freeze["research_outcome_protocol"]["future_returns_and_excursions_are_research_targets_only"] is True
    assert freeze["research_outcome_protocol"]["results_must_be_labelled_development_evidence_not_unseen_validation"] is True


def test_candidate_inputs_are_frozen_and_point_in_time() -> None:
    freeze = load_freeze()
    thresholds = freeze["point_in_time_adaptive_thresholds"]
    controls = freeze["controls"]
    assert controls["candidate_input_definition_frozen"] is True
    assert controls["candidate_regime_assignment_logic_frozen"] is True
    assert thresholds["threshold_history_uses_only_values_available_through_t_minus_1"] is True
    assert thresholds["percentiles_are_computed_per_vehicle"] is True
    assert thresholds["no_cross_vehicle_future_or_contemporaneous_information_may_enter_thresholds"] is True
    assert freeze["price_basis"]["minimum_history_before_candidate_label"] == 452


def test_regime_rules_preserve_neutral_and_no_action() -> None:
    logic = load_freeze()["candidate_regime_assignment_logic"]
    assert logic["logic_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert logic["assignment_order"] == [
        "ELIGIBILITY_GATE",
        "TREND_PERSISTENCE",
        "MEAN_REVERSION_OR_EXHAUSTION",
        "NEUTRAL_OR_UNCERTAIN",
    ]
    assert logic["trend_persistence"]["all_five_conditions_are_required"] is True
    assert logic["mean_reversion_or_exhaustion"]["minimum_exhaustion_conditions_required"] == 2
    assert logic["mean_reversion_or_exhaustion"]["v2_failure_alone_may_not_satisfy_any_condition"] is True
    assert logic["neutral_or_uncertain"]["default_when_evidence_conflicts"] is True
    assert logic["neutral_or_uncertain"]["may_not_be_forced_into_directional_family"] is True
    assert logic["action_mapping"]["authorized"] is False


def test_labels_must_precede_outcome_comparison_and_rule_changes() -> None:
    protocol = load_freeze()["research_outcome_protocol"]
    assert protocol["candidate_labels_must_be_materialized_before_outcome_columns_are_calculated_or_joined"] is True
    assert protocol["label_ledger_hash_must_be_recorded_before_outcome_comparison"] is True
    assert protocol["subsequent_return_horizons_trading_days"] == [21, 63, 126]
    assert protocol["subsequent_mae_mfe_horizons_trading_days"] == [21, 63, 126]
    assert protocol["no_threshold_or_rule_may_be_changed_after_label_ledger_materialization_without_new_version_and_new_governance_decision"] is True


def test_exposure_family_and_support_controls_are_preserved() -> None:
    support = load_freeze()["support_and_exposure_family_controls"]
    assert support["minimum_compared_group_support"] == 20
    assert support["bil_is_reference_control_only"] is True
    assert support["bil_may_not_be_treated_as_opportunity"] is True
    assert support["known_non_independent_groups"] == [["GLD", "IAU", "SGOL"], ["SIVR", "SLV"]]
    assert support["duplicate_family_members_may_not_be_counted_as_independent_confirmations"] is True


def test_freeze_does_not_authorize_downstream_policy_or_validation() -> None:
    controls = load_freeze()["controls"]
    assert controls["v3_historical_regime_research_execution_authorized"] is True
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
        assert controls[key] is False
    assert load_freeze()["next_decision"] == "EXECUTE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH_USING_FROZEN_RULES"


def test_freeze_verifier_is_static_and_does_not_generate_outcomes() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    forbidden = (
        "yfinance",
        "yf.download(",
        ".history(",
        ".pct_change(",
        "duckdb.connect(",
        "pandas.read_csv(",
    )
    for token in forbidden:
        assert token not in source
