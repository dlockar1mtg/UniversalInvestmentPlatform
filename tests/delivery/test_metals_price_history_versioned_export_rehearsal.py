from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_export_rehearsal_files_exist() -> None:
    assert (ROOT / "config" / "presentation" / "metals_price_history_versioned_export_rehearsal.json").is_file()
    assert (ROOT / "scripts" / "rehearse_metals_price_history_versioned_export.py").is_file()


def test_export_rehearsal_locks_governance() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_price_history_versioned_export.py").read_text(encoding="utf-8")
    assert "BEGIN READ ONLY" in text
    assert "metals_vehicle_observations" in text
    assert '"production_database_write_executed": False' in text
    assert '"presentation_activation_executed": False' in text
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
    assert "INSERT INTO" not in text.upper()
    assert "UPDATE " not in text.upper()
    assert "DELETE FROM" not in text.upper()


def test_export_rehearsal_requires_versioned_files_and_hashes() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_price_history_versioned_export.py").read_text(encoding="utf-8")
    assert "metals_current_price.jsonl" not in text
    assert "current_price_filename" in text
    assert "price_history_filename" in text
    assert "manifest_filename" in text
    assert "sha256_file" in text
    assert '"manifest_sha256"' in text
    assert "8283" not in text
    assert 'contract["expected_history_point_count"]' in text
