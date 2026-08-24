from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_activation_contract_exists() -> None:
    path = ROOT / "config" / "presentation" / "dash_read_1_metals_momentum_activation_rehearsal.json"
    assert path.exists()


def test_activation_script_locks_expected_bundle_and_safety() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_momentum_presentation_activation.py").read_text(encoding="utf-8")
    assert "DASH-READ-1-METALS-MOMENTUM-ACTIVATION-REHEARSAL-1" in text
    assert "7bef2ada719080b47d0bf12c4048755bd9f3307636e140e3a8297f9ba3ed560f" not in text
    assert "publish_presentation_bundle" in text
    assert "invalid replacement unexpectedly succeeded" in text
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text


def test_activation_script_does_not_write_analytical_database() -> None:
    text = (ROOT / "scripts" / "rehearse_metals_momentum_presentation_activation.py").read_text(encoding="utf-8")
    assert "duckdb.connect(str(database), read_only=True)" in text
    assert '"production_analytical_database_write_executed": False' in text
