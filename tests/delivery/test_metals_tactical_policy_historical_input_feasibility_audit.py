from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_historical_input_feasibility_contract_exists() -> None:
    assert (ROOT / "config" / "metals" / "tactical_policy_historical_input_feasibility_audit.json").exists()


def test_historical_input_feasibility_uses_certified_package_only() -> None:
    text = (ROOT / "scripts" / "audit_metals_tactical_policy_historical_input_feasibility.py").read_text(encoding="utf-8")
    assert "metals_price_history.jsonl" in text
    assert "expected_history_sha256" in text
    assert "metals_vehicle_observations" not in text
    assert "psycopg" not in text
    assert "duckdb" not in text


def test_historical_input_feasibility_is_point_in_time_and_no_outcomes() -> None:
    text = (ROOT / "scripts" / "audit_metals_tactical_policy_historical_input_feasibility.py").read_text(encoding="utf-8")
    assert "point_in_time_features" in text
    assert '"future_values_used_in_feature_calculation": False' in text
    assert '"forward_outcomes_calculated": False' in text
    assert '"current_only_evidence_backfill_executed": False' in text


def test_historical_input_feasibility_locks_governance() -> None:
    text = (ROOT / "scripts" / "audit_metals_tactical_policy_historical_input_feasibility.py").read_text(encoding="utf-8")
    assert '"historical_candidate_evaluation_authorized": False' in text
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
