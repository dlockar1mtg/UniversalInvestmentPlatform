from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_publication_rehearsal_contract_exists() -> None:
    path = ROOT / "config" / "metals" / "momentum_state_publication_rehearsal_contract.json"
    assert path.exists()


def test_publication_rehearsal_script_locks_semantics() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_current_momentum_state_publication.py").read_text(encoding="utf-8")
    assert "METALS-MOMENTUM-PUBLICATION-REHEARSAL-1" in text
    assert "DESCRIPTIVE_CURRENT_MARKET_STATE_NOT_FORWARD_RETURN_FORECAST" not in text
    assert "metals_momentum_state" not in text
    assert '"tactical_posture": None' in text
    assert '"cross_domain_rank": None' in text
    assert '"presentation_activation_authorized": False' in text
    assert '"production_database_write_executed": False' in text
    assert "metals:vehicle:" in text


def test_publication_rehearsal_parameterizes_like_pattern() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_current_momentum_state_publication.py").read_text(encoding="utf-8")
    assert "asset_id LIKE %s" in text
    assert '(active_id, "metals:vehicle:%")' in text
    assert "asset_id LIKE 'metals:vehicle:%'" not in text


def test_publication_rehearsal_does_not_mutate_postgres() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_current_momentum_state_publication.py").read_text(encoding="utf-8")
    assert 'connection.execute("BEGIN READ ONLY")' in text
    assert "INSERT INTO" not in text.upper()
    assert "UPDATE " not in text.upper()
    assert "DELETE FROM" not in text.upper()
    assert "publish_presentation_bundle" not in text
