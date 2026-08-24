from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "execute_metals_tactical_policy_v3_historical_regime_research.py"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_historical_regime_research_execution.py"
FREEZE = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_freeze.json"


def test_runner_and_verifier_exist_and_parse() -> None:
    assert RUNNER.is_file()
    assert VERIFIER.is_file()
    ast.parse(RUNNER.read_text(encoding="utf-8"))
    ast.parse(VERIFIER.read_text(encoding="utf-8"))


def test_runner_uses_frozen_authority_and_unadjusted_close_only() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "tactical_policy_v3_historical_regime_research_freeze.json" in source
    assert "UNADJUSTED_CLOSE" not in source or "unadjusted_close" in source
    assert '"unadjusted_close", "raw_close", "close"' in source
    assert "adjusted_close" not in source.lower()
    assert "adj_close" not in source.lower()


def test_runner_has_no_network_database_or_production_write_capability() -> None:
    source = RUNNER.read_text(encoding="utf-8").lower()
    forbidden = (
        "requests.",
        "urllib",
        "http://",
        "https://",
        "yfinance",
        "yf.download",
        "duckdb.connect",
        "sqlite3.connect",
        "psycopg",
        "sqlalchemy",
    )
    for token in forbidden:
        assert token not in source


def test_label_ledger_is_written_and_hashed_before_outcomes_are_calculated() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    write_position = source.index("labels.to_csv(ledger_path")
    hash_position = source.index("ledger_sha = sha256_file(ledger_path)")
    outcomes_position = source.index("outcomes = calculate_outcomes(history, labels, horizons)")
    assert write_position < hash_position < outcomes_position


def test_runner_preserves_frozen_rule_version_and_candidate_families() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "METALS-V3-REGIME-CANDIDATE-RULES-1" not in source or "rule_version" in source
    assert '"TREND_PERSISTENCE"' in source
    assert '"MEAN_REVERSION_OR_EXHAUSTION"' in source
    assert '"NEUTRAL_OR_UNCERTAIN"' in source
    assert "ALL_FROZEN_TREND_PERSISTENCE_CONDITIONS_MET" in source
    assert "FROZEN_STRONG_MOMENTUM_AND_EXHAUSTION_CONDITIONS_MET" in source
    assert "FROZEN_DIRECTIONAL_REGIME_CONDITIONS_NOT_SATISFIED" in source


def test_runner_preserves_bil_and_duplicate_exposure_family_controls() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert '{"GLD", "IAU", "SGOL"}' in source
    assert '{"SIVR", "SLV"}' in source
    assert 'symbol == "BIL"' in source
    assert 'return "REFERENCE_CONTROL"' in source


def test_execution_outputs_are_development_not_validation() -> None:
    runner = RUNNER.read_text(encoding="utf-8")
    verifier = VERIFIER.read_text(encoding="utf-8")
    for source in (runner, verifier):
        assert "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE" in source
        assert "unseen_validation_claim_authorized" in source
        assert "regime_definition_authorized" in source
        assert "tactical_posture_authorized" in source
    assert '"unseen_validation_claim_authorized": False' in runner
    assert '"regime_definition_authorized": False' in runner
    assert '"tactical_posture_authorized": False' in runner


def test_execution_verifier_requires_certified_history_shape() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    assert 'history_row_count", -1)) != 10274' in source
    assert 'vehicle_count", -1)) != 11' in source
    assert 'observations_per_vehicle", -1)) != 934' in source
    assert 'label_ledger_row_count", -1)) != 10274' in source


def test_execution_verifier_checks_label_hash_and_required_disclosures() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    assert "label ledger SHA-256 file does not match ledger" in source
    assert "manifest label ledger SHA-256 does not match ledger" in source
    assert "overlapping_forward_windows_present" in source
    assert "v1_v2_intervals_remain_consumed" in source
    assert "development_evidence_not_unseen_validation" in source


def test_freeze_remains_present_as_execution_authority() -> None:
    assert FREEZE.is_file()
