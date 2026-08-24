from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_candidate_rule_design.json"
SCRIPT_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v2_candidate_rule_design.py"


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v2_candidate_rule_files_exist() -> None:
    assert CONTRACT_PATH.is_file()
    assert SCRIPT_PATH.is_file()


def test_v2_candidate_rule_preserves_governed_scope() -> None:
    contract = load_contract()
    assert contract["design_id"] == "METALS-TACTICAL-POLICY-V2-CANDIDATE-RULE-DESIGN-1"
    assert contract["source_research_design"] == "METALS-TACTICAL-POLICY-V2-RESEARCH-DESIGN-1"
    assert len(contract["eligible_vehicle_asset_ids"]) == 10
    assert contract["reference_control_asset_ids"] == ["metals:vehicle:BIL"]
    assert len(contract["historical_validation_input_scope"]["required_price_derived_inputs"]) == 7


def test_v2_candidate_rule_changes_are_explicit_and_prelocked() -> None:
    contract = load_contract()
    rationale = contract["v2_change_rationale"]
    validation = contract["validation_requirements"]
    assert rationale["negative_signal_sensitivity_increased"] is True
    assert rationale["defensive_score_region_broadened_to_include_minus_one"] is True
    assert rationale["changes_use_consumed_v1_findings_as_research_only"] is True
    assert rationale["no_new_unseen_validation_outcomes_used"] is True
    assert validation["minimum_compared_group_support"] == 20
    assert validation["new_validation_interval_must_be_disjoint_from_v1"] is True
    assert validation["candidate_rules_locked_before_new_validation_history_collection"] is True
    assert validation["candidate_rules_locked_before_new_validation_outcome_inspection"] is True


def test_v2_downside_semantics_are_corrected() -> None:
    contract = load_contract()
    validation = contract["validation_requirements"]
    semantic = contract["semantic_constraints"]
    assert validation["defensive_63d_mean_maximum_adverse_excursion_must_be_more_negative_than_constructive"] is True
    assert semantic["defensive_signal_is_downside_warning"] is True
    assert semantic["more_negative_future_mae_is_evidence_consistent_with_defensive_warning"] is True


def test_v2_does_not_authorize_new_validation_or_live_posture() -> None:
    controls = load_contract()["controls"]
    assert controls["v2_candidate_rule_design_authorized"] is True
    for key in (
        "historical_expansion_feasibility_audit_authorized",
        "historical_expansion_execution_authorized",
        "new_validation_outcome_inspection_authorized",
        "historical_candidate_evaluation_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        assert controls[key] is False
