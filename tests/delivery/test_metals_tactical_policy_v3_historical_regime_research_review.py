from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEWER = ROOT / "scripts" / "review_metals_tactical_policy_v3_historical_regime_research_results.py"


def test_reviewer_exists_and_parses() -> None:
    assert REVIEWER.is_file()
    ast.parse(REVIEWER.read_text(encoding="utf-8"))


def test_reviewer_binds_certified_execution_and_ledger() -> None:
    source = REVIEWER.read_text(encoding="utf-8")
    assert "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-EXECUTION-1" in source
    assert "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1" in source
    assert "METALS-V3-REGIME-CANDIDATE-RULES-1" in source
    assert "41f00a74c8116c59b5e36dc039db43a2481ffce9f1ce663da00c270d8c483dfd" in source


def test_reviewer_reads_only_persisted_outputs() -> None:
    source = REVIEWER.read_text(encoding="utf-8").lower()
    forbidden = (
        "requests.", "urllib", "http://", "https://", "yf.download",
        "duckdb.connect", "sqlite3.connect", "psycopg", "sqlalchemy",
        "calculate_outcomes(", "classify_vehicle(", "build_vehicle_features(",
    )
    for token in forbidden:
        assert token not in source


def test_reviewer_requires_support_family_and_three_horizon_review() -> None:
    source = REVIEWER.read_text(encoding="utf-8")
    assert 'DIRECTIONAL = ("TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION")' in source
    assert 'HORIZONS = (21, 63, 126)' in source
    assert "directional_support_gate" in source
    assert "directional_family_gate" in source
    assert "return_direction_consistency" in source


def test_reviewer_preserves_overlap_and_duplicate_family_limits() -> None:
    source = REVIEWER.read_text(encoding="utf-8")
    assert '"observation_counts_are_not_independent_sample_counts": True' in source
    assert '"duplicate_exposure_families_are_not_independent_confirmation": True' in source
    assert '"overlapping_forward_windows_present": True' in source


def test_reviewer_does_not_authorize_regime_or_tactical_posture() -> None:
    source = REVIEWER.read_text(encoding="utf-8")
    assert '"regime_definition_authorized": False' in source
    assert '"tactical_posture_authorized": False' in source
    assert '"development_evidence_not_unseen_validation": True' in source


def test_reviewer_has_fail_closed_next_decision() -> None:
    source = REVIEWER.read_text(encoding="utf-8")
    assert "CONSIDER_LOCKING_METALS_TACTICAL_POLICY_V3_REGIME_DEFINITION" in source
    assert "DESIGN_NEXT_METALS_TACTICAL_POLICY_V3_REGIME_RESEARCH_ITERATION" in source
