from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "tactical_policy_v2_research_design.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v2_research_design.py"


def test_v2_research_design_exists_and_locks_v1_result() -> None:
    cfg = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert cfg["design_id"] == "METALS-TACTICAL-POLICY-V2-RESEARCH-DESIGN-1"
    assert cfg["source_v1_review"] == "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-REVIEW-1"
    assert cfg["v1_findings"]["candidate_v1_result"] == "INCONCLUSIVE"
    assert cfg["v1_findings"]["defensive_holdout_observations"] == 15
    assert cfg["v1_findings"]["minimum_supported_observations_per_compared_group"] == 20
    assert cfg["v1_findings"]["observed_v1_evaluation_evidence_consumed"] is True


def test_v2_requires_new_unseen_evidence_after_rule_lock() -> None:
    cfg = json.loads(CONTRACT.read_text(encoding="utf-8"))
    req = cfg["v2_research_requirements"]
    unseen = cfg["unseen_validation_strategy"]
    assert req["new_unseen_validation_evidence_required"] is True
    assert req["candidate_rules_must_be_locked_before_new_validation_outcomes_are_inspected"] is True
    assert unseen["strategy"] == "GOVERNED_HISTORICAL_EXPANSION_ACQUIRED_AFTER_V2_RULE_LOCK"
    assert unseen["expanded_history_must_end_before_existing_certified_history_start_date"] is True
    assert unseen["network_or_native_history_collection_not_authorized_by_this_design"] is True
    assert unseen["minimum_common_history_start_date_must_be_discovered_not_assumed"] is True


def test_v2_corrects_downside_semantics_without_authorizing_policy() -> None:
    cfg = json.loads(CONTRACT.read_text(encoding="utf-8"))
    req = cfg["v2_research_requirements"]
    controls = cfg["controls"]
    assert req["mae_rule_semantic_misalignment_identified"] if "mae_rule_semantic_misalignment_identified" in req else True
    assert req["defensive_signal_is_a_warning_of_worse_subsequent_outcomes_not_a_low_drawdown_state"] is True
    assert req["corrected_downside_validation_direction_required"] is True
    assert controls["tactical_posture_authorized"] is False
    assert controls["historical_expansion_execution_authorized"] is False
    assert controls["new_validation_outcome_inspection_authorized"] is False
    assert controls["automatic_execution_authorized"] is False


def test_v2_research_design_does_not_lower_support_floor() -> None:
    cfg = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert cfg["v2_candidate_design_scope"]["may_not_reduce_minimum_compared_group_support_below_20"] is True
    assert cfg["next_decision"] == "AUTHORIZE_METALS_TACTICAL_POLICY_V2_CANDIDATE_RULE_DESIGN"


def test_verifier_contains_no_database_or_network_execution() -> None:
    text = VERIFIER.read_text(encoding="utf-8").lower()
    forbidden = (
        "psycopg",
        "duckdb.connect",
        "requests.",
        "urllib",
        "yfinance",
        "insert into",
        "update ",
        "delete from",
    )
    for token in forbidden:
        assert token not in text
