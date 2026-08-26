from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "final_decision_arbitration_with_forward_validation_design.json"


def load_design():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_design_identity_and_sources():
    d = load_design()
    assert d["design_id"] == "METALS-FINAL-DECISION-ARBITRATION-WITH-FORWARD-VALIDATION-DESIGN-1"
    assert d["source_governed_head"] == "6463c704a7fe1c0b71aeec3a12e73877628b506e"
    assert d["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert d["source_limited_historical_evidence_assessment_id"] == "METALS-NATIVE-URANIUM-LIMITED-HISTORICAL-EVIDENCE-ASSESSMENT-1"
    assert d["source_policy_authority"] == "INSUFFICIENT_FOR_UNIVERSAL_POLICY_CERTIFICATION"


def test_final_taxonomy_excludes_decision_conflict():
    d = load_design()
    assert "DECISION_CONFLICT" not in d["final_action_taxonomy"]
    assert "REFERENCE_CONTROL" in d["final_action_taxonomy"]


def test_exact_current_asset_actions():
    d = load_design()
    assert d["current_asset_action_design"] == {
        "metals:commodity:gold": "HOLD",
        "metals:commodity:uranium": "HOLD",
        "metals:vehicle:BIL": "REFERENCE_CONTROL",
        "metals:vehicle:COPX": "HOLD",
        "metals:vehicle:CPER": "HOLD",
        "metals:vehicle:GLD": "WATCH",
        "metals:vehicle:IAU": "WATCH",
        "metals:vehicle:PPLT": "WATCH",
        "metals:vehicle:SGOL": "WATCH",
        "metals:vehicle:SIVR": "WATCH",
        "metals:vehicle:SLV": "WATCH",
        "metals:vehicle:URA": "HOLD",
    }


def test_conflicted_bullish_assets_are_watch_not_conflict_or_buy():
    d = load_design()
    actions = d["current_asset_action_design"]
    for asset in [
        "metals:vehicle:GLD",
        "metals:vehicle:IAU",
        "metals:vehicle:PPLT",
        "metals:vehicle:SGOL",
        "metals:vehicle:SIVR",
        "metals:vehicle:SLV",
    ]:
        assert actions[asset] == "WATCH"


def test_policy_authority_is_explicitly_provisional_and_forward_validated():
    d = load_design()
    assert d["arbitration_policy"]["policy_authority_label"] == "POLICY_DRIVEN_PENDING_FORWARD_EMPIRICAL_VALIDATION"
    assert d["governance_principles"]["policy_driven_arbitration_must_be_labeled_not_empirically_certified"] is True
    assert d["governance_principles"]["forward_validation_required_for_independent_sample_growth"] is True
    assert d["governance_principles"]["final_policy_must_be_replayable_on_future_mature_outcomes"] is True


def test_no_new_numeric_thresholds_or_uranium_overreach():
    d = load_design()
    assert d["governance_principles"]["no_new_numeric_thresholds_created"] is True
    assert d["arbitration_policy"]["historical_evidence_rule"] == "LIMITED_URANIUM_HISTORY_MAY_SUPPORT_EXPLANATION_ONLY_AND_MAY_NOT_CHANGE_CROSS_ASSET_POLICY"
    assert d["fail_closed_rules"]["do_not_count_uranium_shared_outcome_as_eight_trials"] is True
    assert d["fail_closed_rules"]["do_not_claim_policy_is_empirically_certified"] is True


def test_tactical_and_risk_do_not_become_ungoverned_action_overrides():
    d = load_design()
    assert "may not change" in d["arbitration_policy"]["risk_rule"].lower()
    assert "may not change" in d["arbitration_policy"]["tactical_rule"].lower()


def test_forward_validation_contract_all_true():
    d = load_design()
    assert len(d["forward_validation_contract"]) == 12
    assert all(value is True for value in d["forward_validation_contract"].values())


def test_required_output_contract_exact():
    d = load_design()
    assert set(d["required_outputs_for_future_implementation"].keys()) == {
        "final_action_policy_json",
        "twelve_asset_final_action_matrix_json",
        "final_action_explanation_contract_json",
        "forward_validation_anchor_contract_json",
        "final_action_policy_summary_json",
    }
    assert all(value is True for value in d["required_outputs_for_future_implementation"].values())


def test_fail_closed_rules_all_true():
    d = load_design()
    assert len(d["fail_closed_rules"]) == 10
    assert all(value is True for value in d["fail_closed_rules"].values())


def test_all_execution_boundaries_closed():
    d = load_design()
    assert len(d["boundaries"]) == 15
    assert all(value is False for value in d["boundaries"].values())


def test_decision_and_next_decision():
    d = load_design()
    assert d["design_decision"] == "APPROVE_METALS_FINAL_DECISION_ARBITRATION_WITH_FORWARD_VALIDATION_DESIGN_FOR_IMPLEMENTATION_AUTHORIZATION_CONSIDERATION"
    assert d["next_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_DECISION_ARBITRATION_IMPLEMENTATION"
