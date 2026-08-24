from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_market_history_audit_is_read_only_and_fail_closed() -> None:
    source = (ROOT / "scripts/audit_metals_market_history_authority.py").read_text(encoding="utf-8")
    assert "UIIP_DATABASE_URL" in source
    assert "metals_observations" in source
    assert "metals_vehicle_observations" in source
    assert "metals_native_runs" in source
    assert "load_metals_registry" in source
    assert '"momentum_policy_authorized": False' in source
    assert '"tactical_posture_authorized": False' in source
    assert '"automatic_execution_authorized": False' in source
    assert '"next_decision": "ASSESS_METALS_MARKET_HISTORY_COVERAGE_FOR_AUTHORITY_BINDING"' in source
    assert "INSERT " not in source
    assert "UPDATE " not in source
    assert "DELETE " not in source
    assert "CREATE TABLE" not in source


def test_market_history_audit_reports_coverage_and_registry_reconciliation() -> None:
    source = (ROOT / "scripts/audit_metals_market_history_authority.py").read_text(encoding="utf-8")
    for token in (
        '"benchmark_history"',
        '"vehicle_history"',
        '"registry_reconciliation"',
        '"enabled_without_history"',
        '"unknown_history_tickers"',
        '"underlying_coverage"',
        '"current_price_authority_candidate"',
        '"historical_chart_authority_candidate"',
        '"benchmark_history_authority_candidate"',
    ):
        assert token in source
