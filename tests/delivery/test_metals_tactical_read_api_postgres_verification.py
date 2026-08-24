from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_read_api_verifier_is_fail_closed_and_read_only() -> None:
    source = (ROOT / "scripts/verify_metals_tactical_read_api_postgres.py").read_text(encoding="utf-8")
    assert 'EXPECTED_PUBLICATION_ID = "dash-read-1-metals-tactical-dff98e56d27c"' in source
    assert 'EXPECTED_SOURCE_SHA256 = "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"' in source
    assert 'EXPECTED_FINGERPRINT = "fa76508d2c009a644eba9eabaef3600eb96459441336577a16c5f97299f9dda0"' in source
    assert "EXPECTED_RECORD_COUNT = 4171" in source
    assert 'repository.recommendation_catalog(domain_id="metals", limit=200, offset=0)' in source
    assert 'repository.asset_detail("metals", gold_id)' in source
    assert 'repository.asset_detail("metals", gld_id)' in source
    assert 'repository.lineage("metals", gold_id)' in source
    assert 'repository.lineage("metals", gld_id)' in source
    assert '"tactical_posture_authorized": False' in source
    assert '"automatic_execution_authorized": False' in source
    assert '"next_decision": "AUTHORIZE_METALS_MARKET_HISTORY_AUTHORITY_AUDIT"' in source
    assert ".execute(" not in source


def test_read_api_verifier_bootstraps_repository_root_for_direct_execution() -> None:
    source = (ROOT / "scripts/verify_metals_tactical_read_api_postgres.py").read_text(encoding="utf-8")
    assert "ROOT = Path(__file__).resolve().parents[1]" in source
    assert "sys.path.insert(0, str(ROOT))" in source
