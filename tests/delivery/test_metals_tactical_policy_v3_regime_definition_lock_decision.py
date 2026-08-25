from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "config" / "metals" / "tactical_policy_v3_regime_definition_lock_decision.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_regime_definition_lock_decision.py"


def load_decision() -> dict:
    return json.loads(DECISION.read_text(encoding="utf-8"))


def test_decision_and_verifier_exist_and_parse() -> None:
    assert DECISION.is_file()
    assert VERIFIER.is_file()
    ast.parse(VERIFIER.read_text(encoding="utf-8"))


def test_lock_is_bound_to_certified_review_and_frozen_rules() -> None:
    data = load_decision()
    assert data["source_review_id"] == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-REVIEW-1"
    assert data["source_execution_id"] == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-EXECUTION-1"
    assert data["source_freeze_id"] == "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1"
    assert data["source_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert data["source_label_ledger_sha256"] == "41f00a74c8116c59b5e36dc039db43a2481ffce9f1ce663da00c270d8c483dfd"
    assert data["source_review_status"] == "SUFFICIENT_FOR_REGIME_DEFINITION_LOCK_CONSIDERATION"


def test_regime_definition_is_locked_without_action_mapping() -> None:
    data = load_decision()
    locked = data["locked_regime_definition"]
    scope = data["scope_of_lock"]
    assert locked["definition_id"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1"
    assert locked["classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert locked["candidate_regime_families"] == [
        "TREND_PERSISTENCE",
        "MEAN_REVERSION_OR_EXHAUSTION",
        "NEUTRAL_OR_UNCERTAIN",
    ]
    assert scope["regime_definition_authorized"] is True
    assert scope["regime_definition_locked"] is True
    assert scope["action_mapping_authorized"] is False
    assert scope["candidate_tactical_posture_authorized"] is False
    assert scope["live_tactical_posture_authorized"] is False


def test_validation_boundary_stays_fail_closed() -> None:
    data = load_decision()
    boundary = data["validation_boundary"]
    assert boundary["development_evidence_is_not_unseen_validation"] is True
    assert boundary["v1_v2_intervals_remain_consumed"] is True
    assert boundary["new_unseen_validation_authority_required_before_live_tactical_use"] is True
    assert boundary["future_action_mapping_must_be_frozen_before_new_unseen_validation_outcomes_are_inspected"] is True


def test_no_downstream_authority_is_pregranted() -> None:
    data = load_decision()
    scope = data["scope_of_lock"]
    for key in (
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "native_source_query_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        assert scope[key] is False


def test_verifier_is_static_and_read_only() -> None:
    source = VERIFIER.read_text(encoding="utf-8").lower()
    for token in (
        "requests.", "urllib", "http://", "https://", "yfinance", "yf.download",
        "duckdb.connect", "sqlite3.connect", "psycopg", "sqlalchemy",
        "to_csv(", "write_text(", "open(\"w", "open('w",
    ):
        assert token not in source


def test_next_decision_is_action_mapping_design_only() -> None:
    data = load_decision()
    assert data["next_decision"] == "DESIGN_METALS_TACTICAL_POLICY_V3_ACTION_MAPPING"
