from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_price_history_read_api_contract_exists() -> None:
    assert (ROOT / "config" / "presentation" / "metals_price_history_read_api_verification.json").exists()


def test_price_history_read_api_verifier_uses_presentation_repository() -> None:
    text = (ROOT / "scripts" / "verify_metals_price_history_read_api.py").read_text(encoding="utf-8")
    assert "PresentationReadRepository" in text
    assert "asset_detail" in text
    assert "BEGIN READ ONLY" in text
    assert "metals_vehicle_observations" not in text
    assert "INSERT INTO" not in text.upper()
    assert "UPDATE " not in text.upper()
    assert "DELETE FROM" not in text.upper()


def test_price_history_read_api_verifier_preserves_missing_authority() -> None:
    text = (ROOT / "scripts" / "verify_metals_price_history_read_api.py").read_text(encoding="utf-8")
    assert "governed_set.issubset(metals_set)" in text
    assert "ungoverned = sorted(metals_set - governed_set)" in text
    assert "fabricated current-price authority" in text
    assert "fabricated price-history authority" in text
    assert '"missing_authority_preserved": True' in text


def test_price_history_read_api_verifier_locks_governance() -> None:
    text = (ROOT / "scripts" / "verify_metals_price_history_read_api.py").read_text(encoding="utf-8")
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
    assert '"presentation_activation_executed": False' in text
