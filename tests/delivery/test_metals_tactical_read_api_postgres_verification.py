from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_read_api_verifier_is_fail_closed_and_read_only() -> None:
    source = (ROOT / "scripts/verify_metals_tactical_read_api_postgres.py").read_text(encoding="utf-8")
    assert 'EXPECTED_PUBLICATION_ID = "dash-read-1-metals-tactical-dff98e56d27c"' in source
    assert 'EXPECTED_SOURCE_SHA256 = "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"' in source
    assert 'EXPECTED_FINGERPRINT = "fa76508d2c009a644eba9eabaef3600eb96459441336577a16c5f97299f9dda0"' in source
    assert "EXPECTED_RECORD_COUNT = 4171" in source
    assert 'EXPECTED_GOLD_ID = "metals:commodity:gold"' in source
    assert 'EXPECTED_GLD_ID = "metals:vehicle:GLD"' in source
    assert 'repository.recommendation_catalog(domain_id="metals", limit=200, offset=0)' in source
    assert 'repository.asset_detail("metals", gold_id)' in source
    assert 'repository.asset_detail("metals", gld_id)' in source
    assert 'repository.lineage("metals", gold_id)' in source
    assert 'repository.lineage("metals", gld_id)' in source
    assert '"catalog_identity_resolution": "CANONICAL_ASSET_ID"' in source
    assert '"tactical_posture_authorized": False' in source
    assert '"automatic_execution_authorized": False' in source
    assert '"next_decision": "AUTHORIZE_METALS_MARKET_HISTORY_AUTHORITY_AUDIT"' in source
    assert ".execute(" not in source


def test_read_api_verifier_does_not_depend_on_optional_display_symbol_for_gld() -> None:
    source = (ROOT / "scripts/verify_metals_tactical_read_api_postgres.py").read_text(encoding="utf-8")
    assert "_find_asset_id" not in source
    assert 'symbol="GLD"' not in source
    assert "missing_expected = sorted({EXPECTED_GOLD_ID, EXPECTED_GLD_ID} - catalog_ids)" in source


def test_read_api_verifier_bootstraps_repository_root_for_direct_execution() -> None:
    source = (ROOT / "scripts/verify_metals_tactical_read_api_postgres.py").read_text(encoding="utf-8")
    assert "ROOT = Path(__file__).resolve().parents[1]" in source
    assert "sys.path.insert(0, str(ROOT))" in source
