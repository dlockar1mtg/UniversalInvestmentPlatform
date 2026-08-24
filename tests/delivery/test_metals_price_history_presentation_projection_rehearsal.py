from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_price_history_projection_contract_exists() -> None:
    path = ROOT / "config" / "presentation" / "metals_price_history_presentation_projection_rehearsal.json"
    assert path.exists()


def test_price_history_projection_is_package_bound_and_read_only() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_price_history_presentation_projection.py").read_text(encoding="utf-8")
    assert "METALS-PRICE-HISTORY-PRESENTATION-PROJECTION-REHEARSAL-1" in text
    assert "metals_current_price.jsonl" in text
    assert "metals_price_history.jsonl" in text
    assert "manifest.json" in text
    assert "BEGIN READ ONLY" in text
    assert "metals_vehicle_observations" not in text
    assert "INSERT INTO" not in text.upper()
    assert "UPDATE " not in text.upper()
    assert "DELETE FROM" not in text.upper()


def test_price_history_projection_preserves_existing_momentum_surface() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_price_history_presentation_projection.py").read_text(encoding="utf-8")
    assert "expected_active_publication_id" in text
    assert "expected_active_fingerprint" in text
    assert "base.content_fingerprint" in text
    assert "active_publication_unchanged" in text
    assert "expected_extended_record_count" in text


def test_price_history_projection_locks_governance() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_price_history_presentation_projection.py").read_text(encoding="utf-8")
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
    assert '"presentation_activation_executed": False' in text
    assert '"native_source_query_executed": False' in text
