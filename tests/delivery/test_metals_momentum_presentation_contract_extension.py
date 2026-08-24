from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_momentum_presentation_extension_contract_exists() -> None:
    path = ROOT / "config" / "presentation" / "dash_read_1_metals_momentum_extension.json"
    assert path.exists()


def test_momentum_presentation_extension_is_fail_closed() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_momentum_presentation_contract_extension.py").read_text(encoding="utf-8")
    assert "DASH-READ-1-METALS-MOMENTUM-STATE" in text
    assert "METALS-MOMENTUM-INTERPRETATION-1" not in text
    assert "metals_momentum_state" not in text
    assert "validate_publication_bundle(base)" in text
    assert "validate_publication_bundle(extended)" in text
    assert "EXPECTED_BASE_RECORD_COUNT = 4171" in text
    assert '"tactical_posture": None' in text
    assert '"cross_domain_rank": None' in text
    assert '"automatic_execution_authorized": False' in text


def test_momentum_presentation_extension_does_not_activate_or_mutate() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_momentum_presentation_contract_extension.py").read_text(encoding="utf-8")
    upper = text.upper()
    assert 'PG.EXECUTE("BEGIN READ ONLY")' in upper
    assert 'CONNECTION.EXECUTE("BEGIN READ ONLY")' in upper
    assert "PUBLISH_PRESENTATION_BUNDLE" not in upper
    assert "INSERT INTO" not in upper
    assert "UPDATE " not in upper
    assert "DELETE FROM" not in upper
    assert '"presentation_activation_authorized": False' in text
    assert '"production_database_write_executed": False' in text
