from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify_metals_market_history_production_authority.py"


def test_verifier_exists_and_is_read_only():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "BEGIN TRANSACTION READ ONLY" in text
    assert "connection.rollback()" in text
    assert "current_price_authority_verified" in text
    assert "historical_price_authority_verified" in text
    assert '"momentum_feature_calculation_authorized": True' in text
    assert '"tactical_posture_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text


def test_verifier_locks_certified_populations_and_lineage():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'EXPECTED_RUN_ID = "metals-market-history-backfill-20260824"' in text
    assert "EXPECTED_VEHICLE_ROWS = 8283" in text
    assert "EXPECTED_BENCHMARK_ROWS = 4522" in text
    assert "EXPECTED_VEHICLE_SERIES = 11" in text
    assert "EXPECTED_BENCHMARK_SERIES = 6" in text
    assert "MIN_ROWS_PER_SERIES = 500" in text
    assert "vehicle_evidence_sha256" in text
    assert "benchmark_evidence_sha256" in text
    assert "summary_evidence_sha256" in text
    assert '"next_decision": "AUTHORIZE_METALS_MOMENTUM_FEATURE_REHEARSAL"' in text
