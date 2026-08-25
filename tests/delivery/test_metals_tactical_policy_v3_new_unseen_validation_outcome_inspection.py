from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXECUTION_PATH = ROOT / "scripts" / "execute_metals_tactical_policy_v3_new_unseen_validation_outcome_inspection.py"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_new_unseen_validation_outcome_inspection.py"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_new_unseen_validation_outcome_inspection_authorization.json"


def test_execution_and_verifier_parse() -> None:
    ast.parse(EXECUTION_PATH.read_text(encoding="utf-8"))
    ast.parse(VERIFIER_PATH.read_text(encoding="utf-8"))


def test_execution_binds_frozen_authorities() -> None:
    source = EXECUTION_PATH.read_text(encoding="utf-8")
    for value in [
        "597a979ad5b5c031b4c15b84e3d8b23389c780e9a3fc5a19bd1b06ca4b61a6d5",
        "3de3cb2d21ff247f78e210372bc5505bf13d5b3fd2475260fc84cfb514d91c7e",
        "69ed6ff5324f148734a8b84e672e028fcd2e17893bfac4b4c402063916dcf205",
        "400aa5792533653eccf7bdfb3dd4b67fddb8f45ad138bda1a7d4ac1c1137bd62",
        "2023-08-22",
        "2026-08-24",
    ]:
        assert value in source


def test_execution_reuses_locked_classifier_not_new_rules() -> None:
    source = EXECUTION_PATH.read_text(encoding="utf-8")
    assert "from execute_metals_tactical_policy_v3_historical_regime_research import" in source
    assert "build_vehicle_features" in source
    assert "classify_vehicle" in source
    assert '"TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE"' in source
    assert '"MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE"' in source
    assert '"NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY"' in source


def test_label_ledger_is_persisted_and_hashed_before_outcomes() -> None:
    source = EXECUTION_PATH.read_text(encoding="utf-8")
    write_pos = source.index("label_ledger.to_csv")
    hash_pos = source.index("label_sha = sha256_file(label_path)")
    outcome_pos = source.index("outcomes = calculate_outcomes")
    assert write_pos < hash_pos < outcome_pos


def test_primary_validation_is_fail_closed() -> None:
    source = EXECUTION_PATH.read_text(encoding="utf-8")
    assert 'if not (support_gate and family_gate):\n        result = "INCONCLUSIVE"' in source
    assert 'elif all(checks.values()):\n        result = "PASS"' in source
    assert 'else:\n        result = "FAIL"' in source
    assert '"secondary_horizons_cannot_substitute_for_primary_failure": True' in source


def test_primary_checks_match_frozen_protocol() -> None:
    source = EXECUTION_PATH.read_text(encoding="utf-8")
    assert 'supportive["median_forward_return_pct"] > defensive["median_forward_return_pct"]' in source
    assert 'supportive["positive_return_rate"] > defensive["positive_return_rate"]' in source
    assert 'supportive["mean_mae_pct"] > defensive["mean_mae_pct"]' in source
    assert 'supportive["observation_count"] >= 20' in source
    assert 'supportive["exposure_family_count"] >= 2' in source


def test_no_network_database_or_live_tactical_authority() -> None:
    source = EXECUTION_PATH.read_text(encoding="utf-8")
    assert "yfinance" not in source
    assert "requests." not in source
    assert "duckdb" not in source.lower()
    assert '"network_collection_executed": False' in source
    assert '"production_database_write_executed": False' in source
    assert '"tactical_posture_authorized": False' in source


def test_verifier_recomputes_governed_result() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    assert 'expected_result = "PASS" if all(expected_checks.values()) else "FAIL"' in source
    assert 'expected_result = "INCONCLUSIVE"' in source
    assert 'require(result["validation_result"] == expected_result' in source
    assert 'require(manifest["label_ledger_sha256"] == sha256_file(label_path)' in source
    assert 'require(manifest["outcome_ledger_sha256"] == sha256_file(outcome_path)' in source


def test_authorization_file_remains_present_and_unchanged_by_execution_test() -> None:
    assert AUTH_PATH.is_file()
    text = AUTH_PATH.read_text(encoding="utf-8")
    assert "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-OUTCOME-INSPECTION-AUTHORIZATION-1" in text
    assert '"new_validation_outcome_inspection_authorized": true' in text
    assert '"live_tactical_posture_authorized": false' in text
