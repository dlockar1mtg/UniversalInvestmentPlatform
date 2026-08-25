from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "config" / "metals" / "tactical_policy_v3_action_mapping_freeze_decision.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_action_mapping_freeze_decision.py"
DESIGN = ROOT / "config" / "metals" / "tactical_policy_v3_action_mapping_design.json"
LOCK = ROOT / "config" / "metals" / "tactical_policy_v3_regime_definition_lock_decision.json"


def test_freeze_files_exist_and_parse() -> None:
    assert DECISION.is_file()
    assert VERIFIER.is_file()
    json.loads(DECISION.read_text(encoding="utf-8"))
    ast.parse(VERIFIER.read_text(encoding="utf-8"))


def test_freeze_binds_certified_design_and_locked_classifier() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert decision["source_action_mapping_design"] == design["design_id"]
    assert decision["source_mapping_version"] == design["candidate_action_mapping"]["mapping_version"]
    assert decision["source_regime_definition"] == lock["locked_regime_definition"]["definition_id"]
    assert decision["source_classifier_rule_version"] == lock["locked_regime_definition"]["classifier_rule_version"]
    assert decision["source_label_ledger_sha256"] == lock["source_label_ledger_sha256"]


def test_exact_action_mapping_is_frozen() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    mapping = decision["frozen_action_mapping"]
    assert mapping["mapping_version"] == "METALS-V3-ACTION-MAPPING-1"
    assert mapping["TREND_PERSISTENCE"] == "TACTICAL_SUPPORTIVE"
    assert mapping["MEAN_REVERSION_OR_EXHAUSTION"] == "TACTICAL_DEFENSIVE"
    assert mapping["NEUTRAL_OR_UNCERTAIN"] == "NO_TACTICAL_OVERLAY"
    assert mapping["mapping_is_ordinal_not_position_sizing"] is True
    assert mapping["mapping_does_not_authorize_buy_sell_or_trade_execution"] is True
    assert mapping["neutral_or_uncertain_remains_fail_closed"] is True


def test_unseen_validation_hypothesis_is_frozen_before_inspection() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    hypothesis = decision["frozen_unseen_validation_hypothesis"]
    assert hypothesis["primary_horizon_trading_days"] == 63
    assert hypothesis["secondary_horizons_trading_days"] == [21, 126]
    assert hypothesis["minimum_compared_group_support"] == 20
    assert hypothesis["minimum_distinct_exposure_families_per_directional_state"] == 2
    assert hypothesis["supportive_median_return_should_exceed_defensive"] is True
    assert hypothesis["supportive_positive_return_rate_should_exceed_defensive"] is True
    assert hypothesis["supportive_mean_mae_should_be_less_negative_than_defensive"] is True
    assert hypothesis["all_three_directional_checks_required_at_primary_horizon"] is True


def test_consumed_evidence_and_new_validation_boundaries_remain_closed() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    boundary = decision["validation_boundary"]
    assert boundary["action_mapping_frozen_before_new_unseen_validation_outcome_inspection"] is True
    assert boundary["new_unseen_validation_package_must_postdate_consumed_v1_v2_evidence"] is True
    assert boundary["consumed_v1_v2_intervals_may_not_be_reused_as_unseen_validation"] is True
    assert boundary["new_validation_data_collection_requires_separate_authorization"] is True
    assert boundary["new_validation_outcome_inspection_requires_separate_authorization"] is True


def test_freeze_authorizes_no_live_or_validation_execution_scope() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    scope = decision["scope_of_freeze"]
    assert scope["v3_regime_definition_authorized"] is True
    assert scope["v3_regime_definition_locked"] is True
    assert scope["action_mapping_design_authorized"] is True
    assert scope["action_mapping_frozen"] is True
    for key in (
        "new_validation_data_collection_authorized",
        "new_validation_outcome_inspection_authorized",
        "candidate_tactical_posture_authorized",
        "live_tactical_posture_authorized",
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


def test_next_decision_is_new_unseen_validation_authorization_design() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    assert decision["next_decision"] == "DESIGN_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_AUTHORIZATION"
