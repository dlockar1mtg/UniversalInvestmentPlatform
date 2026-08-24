from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_momentum_read_api_verification_contract_exists() -> None:
    path = ROOT / "config" / "presentation" / "dash_read_1_metals_momentum_read_api_verification.json"
    assert path.exists()


def test_momentum_read_api_verifier_is_read_only() -> None:
    text = (ROOT / "scripts" / "verify_metals_momentum_state_read_api.py").read_text(encoding="utf-8")
    assert "DASH-READ-1-METALS-MOMENTUM-READ-API-VERIFY-1" in text
    assert "PresentationReadRepository" in text
    assert 'repository.asset_detail("metals", asset_id)' in text
    assert "metals_momentum_state" not in text
    assert "INSERT INTO" not in text.upper()
    assert "UPDATE " not in text.upper()
    assert "DELETE FROM" not in text.upper()


def test_momentum_read_api_verifier_locks_governance() -> None:
    text = (ROOT / "scripts" / "verify_metals_momentum_state_read_api.py").read_text(encoding="utf-8")
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
    assert '"production_database_write_executed": False' in text
