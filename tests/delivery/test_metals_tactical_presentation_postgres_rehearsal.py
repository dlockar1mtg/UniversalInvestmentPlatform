from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/rehearse_metals_tactical_presentation_postgres.py"


def test_metals_tactical_postgres_rehearsal_locks_verified_projection() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'EXPECTED_TOTAL_RECORDS = 4171' in source
    assert 'EXPECTED_FINGERPRINT = "fa76508d2c009a644eba9eabaef3600eb96459441336577a16c5f97299f9dda0"' in source
    for record_type, count in (
        ("metals_model_component", 64),
        ("metals_regime_probability", 12),
        ("metals_uncertainty_adjusted", 32),
        ("metals_recommendation_change", 10),
        ("metals_data_freshness", 21),
        ("metals_platform_health", 1),
    ):
        assert f'("metals", "{record_type}", {count})' in source


def test_metals_tactical_postgres_rehearsal_is_directly_executable_and_fail_closed() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "sys.path.insert(0, str(ROOT))" in source
    assert "validate_publication_bundle(publication)" in source
    assert "FAILED_REPLACEMENT_PRESERVES_LAST_GOOD=PASS" in source
    assert "INVALID_PUBLICATION_NEVER_STAGED=PASS" in source
    assert "EXISTING_POSTGRES_APPLICATION_TABLES_PRESERVED=PASS" in source
    assert "METALS_ASSET_DETAIL_TACTICAL_EVIDENCE=PASS" in source
