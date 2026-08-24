from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_export_review_contract_exists() -> None:
    assert (ROOT / "config" / "presentation" / "metals_price_history_versioned_export_review.json").exists()


def test_export_review_is_read_only() -> None:
    text = (ROOT / "scripts" / "review_metals_price_history_versioned_export.py").read_text(encoding="utf-8")
    assert "METALS-PRICE-HISTORY-VERSIONED-EXPORT-REVIEW-1" in text
    assert "UIIP_DATABASE_URL" not in text
    assert "psycopg" not in text
    assert "duckdb" not in text
    upper = text.upper()
    assert "INSERT INTO" not in upper
    assert "UPDATE " not in upper
    assert "DELETE FROM" not in upper


def test_export_review_locks_exact_artifact_hashes() -> None:
    text = (ROOT / "config" / "presentation" / "metals_price_history_versioned_export_review.json").read_text(encoding="utf-8")
    assert "e18ece1a8dbc5b23f6ec7bb2d014822bdccd8a7f82fca0b6c23d5fda3bc8a4ed" in text
    assert "c3749acbcf3a6d11ee9a6ca392b8421e7654936af489fbb93a2f4ae659470f31" in text
    assert "82ead8e711e0fde4b30fa4e0e7196681e41e7f0ffa363af201c0ee0737473dcf" in text


def test_export_review_locks_governance() -> None:
    text = (ROOT / "config" / "presentation" / "metals_price_history_versioned_export_review.json").read_text(encoding="utf-8")
    assert '"native_source_query_authorized": false' in text
    assert '"export_execution_authorized": false' in text
    assert '"production_database_write_authorized": false' in text
    assert '"presentation_activation_authorized": false' in text
    assert '"tactical_posture_authorized": false' in text
    assert '"cross_domain_rank_authorized": false' in text
    assert '"automatic_execution_authorized": false' in text
