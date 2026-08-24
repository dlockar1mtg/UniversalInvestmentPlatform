from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_regime_research_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_authorization.json"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_historical_regime_research_authorization.py"


def load_design() -> dict[str, object]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def load_auth() -> dict[str, object]:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_extends_certified_regime_design() -> None:
    design = load_design()
    auth = load_auth()
    assert design["design_id"] == "METALS-TACTICAL-POLICY-V3-REGIME-RESEARCH-DESIGN-1"
    assert design["next_decision"] == "AUTHORIZE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH"
    assert auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-AUTHORIZATION-1"
    assert auth["source_v3_regime_research_design"] == design["design_id"]
    assert auth["decision"] == "AUTHORIZE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH"


def test_authorization_is_development_only_on_consumed_evidence() -> None:
    scope = load_auth()["authorization_scope"]
    assert scope["historical_regime_research_execution_authorized"] is True
    assert scope["research_role"] == "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE"
    assert scope["consumed_v1_v2_evidence_may_be_used_for_hypothesis_development"] is True
    assert scope["consumed_v1_v2_intervals_may_not_be_called_unseen_again"] is True
    assert scope["point_in_time_regime_labels_must_be_generated_before_subsequent_outcomes_are_compared"] is True
    assert scope["subsequent_outcomes_may_be_used_only_as_research_targets"] is True
    assert scope["research_results_must_be_labelled_development_evidence_not_unseen_validation"] is True


def test_pre_execution_freeze_is_required() -> None:
    freeze = load_auth()["pre_execution_freeze_requirements"]
    assert freeze["candidate_input_definitions_must_be_versioned_and_frozen_before_execution"] is True
    assert freeze["candidate_regime_assignment_logic_must_be_versioned_and_frozen_before_execution"] is True
    assert freeze["future_returns_or_future_excursions_may_not_be_classifier_inputs"] is True
    assert freeze["current_only_recommendation_or_risk_fields_may_not_be_backfilled_historically"] is True
    assert freeze["missing_historical_vintage_authority_must_remain_missing"] is True
    assert freeze["minimum_compared_group_support"] == 20
    assert freeze["minimum_compared_group_support_may_not_be_lowered"] is True


def test_candidate_regime_and_input_scope_preserves_semantics() -> None:
    auth = load_auth()
    assert auth["authorized_candidate_regime_families"] == [
        "TREND_PERSISTENCE",
        "MEAN_REVERSION_OR_EXHAUSTION",
        "NEUTRAL_OR_UNCERTAIN",
    ]
    inputs = auth["authorized_candidate_input_research_scope"]
    assert inputs["trend_strength_must_be_distinguished_from_trend_persistence"] is True
    assert inputs["conflicting_or_weak_evidence_must_be_allowed_to_resolve_to_neutral_or_uncertain"] is True
    assert inputs["additional_candidate_inputs_are_not_final_authorized_production_features"] is True


def test_exposure_family_controls_are_preserved() -> None:
    exposure = load_auth()["exposure_family_controls"]
    assert exposure["bil_is_reference_control_only"] is True
    assert exposure["bil_may_not_be_treated_as_an_opportunity"] is True
    assert exposure["duplicate_exposure_families_are_not_independent_confirmation"] is True
    assert exposure["known_non_independent_groups"] == [["GLD", "IAU", "SGOL"], ["SIVR", "SLV"]]
    assert exposure["support_must_be_reported_by_exposure_family"] is True
    assert exposure["duplicate_family_members_may_not_be_counted_as_independent_confirmations"] is True


def test_authorization_does_not_pre_authorize_downstream_policy() -> None:
    auth = load_auth()
    controls = auth["controls"]
    assert controls["v3_research_design_authorized"] is True
    assert controls["v3_regime_research_design_authorized"] is True
    assert controls["v3_historical_regime_research_authorized"] is True
    assert controls["v3_historical_regime_research_execution_authorized"] is True
    for key in (
        "v3_regime_definition_authorized",
        "v3_candidate_rule_design_authorized",
        "new_validation_outcome_inspection_authorized",
        "tactical_posture_authorized",
        "production_database_write_authorized",
        "presentation_activation_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        assert controls[key] is False
    assert auth["next_decision"] == "EXECUTE_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH"


def test_verifier_is_static_and_does_not_execute_research() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    forbidden = (
        "yfinance",
        "yf.download(",
        ".history(",
        ".pct_change(",
        "duckdb.connect(",
        "forward_return",
        "maximum_adverse_excursion",
        "maximum_favorable_excursion",
    )
    for token in forbidden:
        assert token not in source
