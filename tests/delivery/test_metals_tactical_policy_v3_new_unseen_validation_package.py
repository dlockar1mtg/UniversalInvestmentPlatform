from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "scripts" / "collect_metals_tactical_policy_v3_new_unseen_validation_package.py"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v3_new_unseen_validation_package.py"
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_new_unseen_validation_authorization.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_package_scripts_and_authorization_exist() -> None:
    assert COLLECTOR.is_file()
    assert VERIFIER.is_file()
    assert AUTH.is_file()


def test_collector_binds_authorized_unseen_interval_and_universe() -> None:
    src = read(COLLECTOR)
    assert 'START_DATE = "2023-08-22"' in src
    assert 'END_DATE = "2026-08-24"' in src
    assert 'DOWNLOAD_END_EXCLUSIVE = "2026-08-25"' in src
    assert 'OPPORTUNITY_TICKERS = ["COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]' in src
    assert 'REFERENCE_TICKER = "BIL"' in src


def test_collector_requires_raw_close_and_auto_adjust_false() -> None:
    src = read(COLLECTOR)
    assert "auto_adjust=False" in src
    assert '"close_usd": float(close_value)' in src
    assert '"required_price_semantics": "UNADJUSTED_CLOSE"' in src
    assert '"auto_adjust": False' in src


def test_collector_is_outcome_blind_and_freezes_hashes() -> None:
    src = read(COLLECTOR)
    assert '"outcome_blind": True' in src
    assert '"package_frozen": True' in src
    assert '"classifier_executed": False' in src
    assert '"validation_outcomes_calculated": False' in src
    assert '"validation_outcomes_inspected": False' in src
    assert '"new_validation_outcome_inspection_authorized": False' in src
    assert '"history_sha256": history_sha' in src
    assert '"coverage_sha256": coverage_sha' in src


def test_collector_refuses_overwrite() -> None:
    src = read(COLLECTOR)
    assert "Output directory already exists; refusing overwrite" in src


def test_verifier_recomputes_hashes_and_forbids_outcome_fields() -> None:
    src = read(VERIFIER)
    assert 'manifest["history_sha256"] == sha256_file(history_path)' in src
    assert 'manifest["coverage_sha256"] == sha256_file(coverage_path)' in src
    assert '"forward_return_63d_pct"' in src
    assert '"candidate_regime"' in src
    assert '"candidate_action_state"' in src
    assert '"validation_result"' in src


def test_verifier_requires_package_to_remain_non_live() -> None:
    src = read(VERIFIER)
    assert 'manifest["validation_outcomes_inspected"] is False' in src
    assert 'manifest["tactical_posture_authorized"] is False' in src
    assert 'manifest["new_validation_outcome_inspection_authorized"] is False' in src


def test_next_decision_is_outcome_inspection_certification_not_live_use() -> None:
    expected = "CERTIFY_AND_AUTHORIZE_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_OUTCOME_INSPECTION"
    assert expected in read(COLLECTOR)
    assert expected in read(VERIFIER)
