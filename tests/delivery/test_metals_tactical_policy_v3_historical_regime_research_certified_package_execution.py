from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "scripts" / "execute_metals_tactical_policy_v3_historical_regime_research_from_certified_package.py"


def test_certified_package_adapter_exists_and_parses() -> None:
    assert ADAPTER.is_file()
    ast.parse(ADAPTER.read_text(encoding="utf-8"))


def test_adapter_binds_exact_certified_v2_package_hashes() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert "400aa5792533653eccf7bdfb3dd4b67fddb8f45ad138bda1a7d4ac1c1137bd62" in source
    assert "26477acb7f50169980ea6c1ede73b6cfac7ffbc21b34273a1253f1ffa6b5f9f9" in source
    assert "602521ce36c4f1cb0797dc29d932c803bd0e0a12c38652211c1cdd1cf32216dd" in source
    assert "metals-v2-validation-history-20191204-20230821" in source


def test_adapter_requires_original_jsonl_artifacts() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert '"metals_v2_validation_history.jsonl"' in source
    assert '"coverage.json"' in source
    assert '"manifest.json"' in source
    assert 'record["close_usd"]' in source
    assert 'record["adjusted_close_usd"]' not in source or "required" in source


def test_adapter_uses_raw_close_and_explicitly_rejects_adjusted_close_use() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert '"raw_close_field"] = "close_usd"' in source
    assert '"adjusted_close_used_for_v3_features_or_outcomes"] = False' in source
    assert 'writer.writerow({"ticker": ticker, "observation_date": date, "close": repr(close)})' in source


def test_adapter_preserves_certified_shape() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert "EXPECTED_HISTORY_ROWS = 10274" in source
    assert "EXPECTED_VEHICLES = 11" in source
    assert "EXPECTED_OBSERVATIONS_PER_VEHICLE = 934" in source
    assert 'if "BIL" not in tickers' in source


def test_adapter_has_no_network_or_database_access() -> None:
    source = ADAPTER.read_text(encoding="utf-8").lower()
    for token in (
        "requests.",
        "urllib",
        "http://",
        "https://",
        "import yfinance",
        "from yfinance",
        "yf.download(",
        "duckdb.connect",
        "sqlite3.connect",
        "psycopg",
        "sqlalchemy",
    ):
        assert token not in source


def test_adapter_rebuilds_provenance_after_ephemeral_normalization() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert "TemporaryDirectory" in source
    assert 'consumed.pop("source_history_csv", None)' in source
    assert 'consumed["source_history_jsonl"]' in source
    assert 'manifest["source_format"] = "CERTIFIED_JSONL_NORMALIZED_IN_EPHEMERAL_TEMPORARY_DIRECTORY"' in source
    assert 'manifest["output_files"]' in source


def test_adapter_preserves_development_only_authority_boundary() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    assert '"regime_definition_authorized": False' in source
    assert '"tactical_posture_authorized": False' in source
    assert '"unseen_validation_claim_authorized": False' in source
