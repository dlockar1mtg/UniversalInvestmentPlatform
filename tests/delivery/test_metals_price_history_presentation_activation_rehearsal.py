from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_price_history_activation_contract_exists() -> None:
    path = ROOT / "config" / "presentation" / "metals_price_history_presentation_activation_rehearsal.json"
    assert path.exists()


def test_price_history_activation_is_package_bound() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_price_history_presentation_activation.py").read_text(encoding="utf-8")
    assert "METALS-PRICE-HISTORY-PRESENTATION-ACTIVATION-REHEARSAL-1" in text
    assert "metals_current_price.jsonl" in text
    assert "metals_price_history.jsonl" in text
    assert "manifest.json" in text
    assert "metals_vehicle_observations" not in text
    assert '"native_source_query_executed": False' in text
    assert '"export_execution_executed": False' in text


def test_price_history_activation_locks_exact_candidate() -> None:
    contract = (ROOT / "config" / "presentation" / "metals_price_history_presentation_activation_rehearsal.json").read_text(encoding="utf-8")
    assert "12476" in contract
    assert "c8742b715c8e6d4120eea6a1d717c0d2ebe7a90e78339f7b17cb4e64ee3d831f" in contract
    text = (ROOT / "scripts" / "rehearse_metals_price_history_presentation_activation.py").read_text(encoding="utf-8")
    assert "expected_extended_fingerprint" in text
    assert "expected_extended_record_count" in text


def test_price_history_activation_preserves_last_good_and_governance() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_price_history_presentation_activation.py").read_text(encoding="utf-8")
    assert "invalid replacement unexpectedly succeeded" in text
    assert "invalid replacement displaced last-good publication" in text
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
    assert '"production_analytical_database_write_executed": False' in text
