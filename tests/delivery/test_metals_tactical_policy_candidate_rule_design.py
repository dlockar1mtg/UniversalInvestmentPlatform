from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_candidate_rule_design_contract_exists() -> None:
    path = ROOT / "config" / "metals" / "tactical_policy_candidate_rule_design.json"
    assert path.exists()


def test_candidate_rule_design_is_pre_specified_and_fail_closed() -> None:
    text = (ROOT / "config" / "metals" / "tactical_policy_candidate_rule_design.json").read_text(encoding="utf-8")
    assert "METALS-TACTICAL-POLICY-CANDIDATE-RULE-DESIGN-1" in text
    assert '"historical_candidate_evaluation_authorized": false' in text
    assert '"tactical_posture_authorized": false' in text
    assert '"candidate_rules_locked_before_forward_outcome_evaluation": true' in text
    assert '"current_only_recommendation_or_risk_may_not_be_backfilled_into_history": true' in text
    assert '"insufficient_current_authority_yields_no_tactical_posture": true' in text


def test_candidate_rule_design_keeps_bil_out_of_opportunity_set() -> None:
    text = (ROOT / "scripts" / "verify_metals_tactical_policy_candidate_rule_design.py").read_text(encoding="utf-8")
    assert 'reference != ["metals:vehicle:BIL"]' in text
    assert '"metals:vehicle:BIL" in eligible' in text
    assert "BIL may not enter the tactical opportunity set" in text


def test_candidate_rule_design_requires_time_aligned_historical_inputs() -> None:
    text = (ROOT / "scripts" / "verify_metals_tactical_policy_candidate_rule_design.py").read_text(encoding="utf-8")
    assert "time_aligned_price_derived_inputs_only" in text
    assert "current_only_recommendation_or_risk_may_not_be_backfilled_into_history" in text
    assert "missing_historical_vintage_authority_must_remain_missing" in text
    assert "forward_horizons_observations" in text
    assert "development_then_holdout_required" in text


def test_candidate_rule_design_does_not_authorize_production_posture() -> None:
    text = (ROOT / "scripts" / "verify_metals_tactical_policy_candidate_rule_design.py").read_text(encoding="utf-8")
    assert '"tactical_posture_authorized": False' in text
    assert '"historical_candidate_evaluation_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
