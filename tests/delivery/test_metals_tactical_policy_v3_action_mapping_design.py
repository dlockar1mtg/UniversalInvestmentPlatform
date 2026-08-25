from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "config" / "metals" / "tactical_policy_v3_action_mapping_design.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_action_mapping_design.py"
LOCK = ROOT / "config" / "metals" / "tactical_policy_v3_regime_definition_lock_decision.json"


def load() -> dict:
    return json.loads(DESIGN.read_text(encoding="utf-8"))


def test_design_and_verifier_exist_and_parse() -> None:
    assert DESIGN.is_file()
    assert VERIFIER.is_file()
    ast.parse(VERIFIER.read_text(encoding="utf-8"))


def test_design_is_bound_to_locked_regime_definition() -> None:
    design = load()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert design["source_regime_definition"] == "METALS-TACTICAL-POLICY-V3-REGIME-DEFINITION-1"
    assert design["source_regime_definition"] == lock["locked_regime_definition"]["definition_id"]
    assert design["source_classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1"
    assert design["source_label_ledger_sha256"] == lock["source_label_ledger_sha256"]


def test_candidate_action_mapping_is_simple_ordinal_and_fail_closed() -> None:
    mapping = load()["candidate_action_mapping"]
    assert mapping["mapping_version"] == "METALS-V3-ACTION-MAPPING-1"
    assert mapping["TREND_PERSISTENCE"]["candidate_action_state"] == "TACTICAL_SUPPORTIVE"
    assert mapping["MEAN_REVERSION_OR_EXHAUSTION"]["candidate_action_state"] == "TACTICAL_DEFENSIVE"
    assert mapping["NEUTRAL_OR_UNCERTAIN"]["candidate_action_state"] == "NO_TACTICAL_OVERLAY"
    for regime in ("TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION", "NEUTRAL_OR_UNCERTAIN"):
        assert mapping[regime]["position_size_change_authorized"] is False
        assert mapping[regime]["trade_execution_authorized"] is False


def test_unseen_validation_hypothesis_is_frozen_before_outcomes() -> None:
    hypothesis = load()["unseen_validation_hypothesis"]
    assert hypothesis["horizons_trading_days"] == [21, 63, 126]
    assert hypothesis["primary_horizon_trading_days"] == 63
    assert hypothesis["minimum_compared_group_support"] == 20
    assert hypothesis["minimum_distinct_exposure_families_per_directional_state"] == 2
    assert hypothesis["supportive_median_return_should_exceed_defensive"] is True
    assert hypothesis["supportive_positive_return_rate_should_exceed_defensive"] is True
    assert hypothesis["supportive_mean_mae_should_be_less_negative_than_defensive"] is True
    assert hypothesis["all_three_directional_checks_required_at_primary_horizon"] is True


def test_design_preserves_new_unseen_validation_boundary() -> None:
    boundary = load()["validation_boundary"]
    assert boundary["new_unseen_validation_package_must_postdate_consumed_v1_v2_evidence"] is True
    assert boundary["new_unseen_validation_data_collection_requires_separate_authorization"] is True
    assert boundary["action_mapping_must_be_frozen_before_new_unseen_outcomes_are_inspected"] is True
    assert boundary["consumed_v1_v2_intervals_may_not_be_reused_as_unseen_validation"] is True
    assert boundary["overlapping_forward_windows_must_be_disclosed"] is True
    assert boundary["support_must_be_reported_by_vehicle_and_exposure_family"] is True


def test_no_downstream_live_authority_is_created() -> None:
    controls = load()["controls"]
    assert controls["v3_regime_definition_locked"] is True
    assert controls["action_mapping_design_authorized"] is True
    for key in (
        "action_mapping_frozen",
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
        assert controls[key] is False


def test_verifier_is_static_and_has_no_network_database_or_outcome_execution() -> None:
    source = VERIFIER.read_text(encoding="utf-8").lower()
    for token in (
        "requests.", "urllib", "http://", "https://", "import yfinance", "from yfinance",
        "yf.download", "duckdb.connect", "sqlite3.connect", "psycopg", "sqlalchemy",
        "pandas.read_csv", "pd.read_csv", "forward_return", "mae_pct", "mfe_pct",
    ):
        assert token not in source
