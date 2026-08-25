from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "foundation" / "import_engine" / "sql" / "009_metals_tactical_state_persistence.sql"
IMPORTER_PATH = ROOT / "scripts" / "persist_metals_tactical_policy_v3_current_state.py"
VERIFIER_PATH = ROOT / "scripts" / "verify_metals_tactical_policy_v3_production_persistence_implementation.py"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_production_persistence_authorization.json"

EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
TICKERS = ["BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]


def load_importer():
    spec = importlib.util.spec_from_file_location("metals_persistence", IMPORTER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_row(ticker: str) -> dict:
    reference = ticker == "BIL"
    return {
        "asset_id": f"metals:vehicle:{ticker}",
        "ticker": ticker,
        "as_of_date": "2026-08-21",
        "candidate_regime": "NEUTRAL_OR_UNCERTAIN",
        "tactical_state": "NO_TACTICAL_OVERLAY",
        "classifier_rule_version": "METALS-V3-REGIME-CANDIDATE-RULES-1",
        "action_mapping_version": "METALS-V3-ACTION-MAPPING-1",
        "price_semantics": "UNADJUSTED_CLOSE",
        "source_package_id": "metals-price-history-20260824",
        "state_available": not reference,
        "state_reason": "REFERENCE_CONTROL_NOT_AN_OPPORTUNITY" if reference else "NEUTRAL_OR_UNCERTAIN_DEFAULT",
        "is_reference_control": reference,
        "return_1m_pct": 1.0,
        "return_3m_pct": 2.0,
        "return_6m_pct": 3.0,
        "distance_ma50_pct": 0.1,
        "distance_ma200_pct": 0.2,
        "current_drawdown_pct": -1.0,
        "realized_volatility_3m_pct": 10.0,
        "trend_slope": 0.01,
        "return_dispersion": 2.0,
        "volatility_change": 0.5,
        "drawdown_recovery_rate": 0.1,
        "distance_from_recent_extreme": -2.0,
        "short_vs_long_momentum_spread": 0.4,
    }


def make_materialization(tmp_path: Path, module) -> Path:
    root = tmp_path / "materialization"
    root.mkdir()
    state_path = root / "metals_v3_current_state.jsonl"
    rows = [source_row(ticker) for ticker in TICKERS]
    with state_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    manifest = {
        "materialization_id": "METALS-TACTICAL-POLICY-V3-CURRENT-STATE-MATERIALIZATION-1",
        "state_sha256": module.sha256_file(state_path),
        "as_of_date": "2026-08-21",
        "row_count": 11,
        "opportunity_row_count": 10,
        "reference_control_row_count": 1,
        "price_semantics": "UNADJUSTED_CLOSE",
        "classifier_rule_version": "METALS-V3-REGIME-CANDIDATE-RULES-1",
        "action_mapping_version": "METALS-V3-ACTION-MAPPING-1",
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return root


def patch_governed_hashes(module, materialization: Path, monkeypatch) -> None:
    state_path = materialization / "metals_v3_current_state.jsonl"
    manifest_path = materialization / "manifest.json"
    monkeypatch.setattr(module, "EXPECTED_STATE_SHA", module.sha256_file(state_path))
    monkeypatch.setattr(module, "EXPECTED_MANIFEST_SHA", module.sha256_file(manifest_path))


def test_authorization_still_blocks_production_write() -> None:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    storage = auth["authorized_storage"]
    assert storage["schema_migration_authorized"] is True
    assert storage["persistence_implementation_authorized"] is True
    assert storage["production_database_write_authorized"] is False


def test_migration_is_append_only_and_current_view_derived() -> None:
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS metals_tactical_state_history" in sql
    assert "CREATE OR REPLACE VIEW metals_tactical_state_current" in sql
    assert "ROW_NUMBER() OVER" in sql
    upper = sql.upper()
    assert "INSERT OR REPLACE" not in upper
    assert "DELETE FROM METALS_TACTICAL_STATE_HISTORY" not in upper
    assert "UPDATE METALS_TACTICAL_STATE_HISTORY" not in upper


def test_importer_and_verifier_exist() -> None:
    assert IMPORTER_PATH.is_file()
    assert VERIFIER_PATH.is_file()


def test_disposable_persistence_exact_readback(tmp_path: Path, monkeypatch) -> None:
    module = load_importer()
    materialization = make_materialization(tmp_path, module)
    patch_governed_hashes(module, materialization, monkeypatch)
    database = tmp_path / "test.duckdb"
    duckdb.connect(str(database)).close()

    result = module.persist(
        database,
        materialization / "metals_v3_current_state.jsonl",
        materialization / "manifest.json",
        datetime(2026, 8, 25, 18, 0, tzinfo=timezone.utc),
    )
    assert result["status"] == "PASS"
    assert result["row_count"] == 11
    assert result["readback_exact_match"] is True

    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT COUNT(*) FROM metals_tactical_state_history").fetchone()[0] == 11
        assert connection.execute("SELECT COUNT(*) FROM metals_tactical_state_current").fetchone()[0] == 11
        assert connection.execute("SELECT COUNT(*) FROM metals_tactical_state_current WHERE is_reference_control").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM metals_tactical_state_current WHERE tactical_state = 'NO_TACTICAL_OVERLAY'").fetchone()[0] == 11


def test_duplicate_exact_import_fails_closed_without_extra_rows(tmp_path: Path, monkeypatch) -> None:
    module = load_importer()
    materialization = make_materialization(tmp_path, module)
    patch_governed_hashes(module, materialization, monkeypatch)
    database = tmp_path / "duplicate.duckdb"
    duckdb.connect(str(database)).close()
    imported_at = datetime(2026, 8, 25, 18, 0, tzinfo=timezone.utc)

    module.persist(database, materialization / "metals_v3_current_state.jsonl", materialization / "manifest.json", imported_at)
    with pytest.raises(RuntimeError, match="duplicate exact tactical-state import already exists"):
        module.persist(database, materialization / "metals_v3_current_state.jsonl", materialization / "manifest.json", imported_at)

    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT COUNT(*) FROM metals_tactical_state_history").fetchone()[0] == 11


def test_failure_rolls_back_schema_and_rows(tmp_path: Path, monkeypatch) -> None:
    module = load_importer()
    materialization = make_materialization(tmp_path, module)
    patch_governed_hashes(module, materialization, monkeypatch)
    database = tmp_path / "rollback.duckdb"
    duckdb.connect(str(database)).close()

    original_rows = module.load_rows(materialization / "metals_v3_current_state.jsonl")
    original_canonical = module.canonical_source_row
    calls = {"count": 0}

    def corrupted(row):
        calls["count"] += 1
        value = original_canonical(row)
        if calls["count"] > 11 and row.get("ticker") == "URNM":
            return value + "CORRUPT"
        return value

    monkeypatch.setattr(module, "canonical_source_row", corrupted)
    with pytest.raises(RuntimeError):
        module.persist(
            database,
            materialization / "metals_v3_current_state.jsonl",
            materialization / "manifest.json",
            datetime(2026, 8, 25, 18, 0, tzinfo=timezone.utc),
        )

    with duckdb.connect(str(database), read_only=True) as connection:
        objects = {row[0] for row in connection.execute("SELECT table_name FROM information_schema.tables").fetchall()}
        assert "metals_tactical_state_history" not in objects


def test_cli_requires_explicit_mode() -> None:
    text = IMPORTER_PATH.read_text(encoding="utf-8")
    assert "--disposable-test-mode" in text
    assert "--production-write-authorization" in text
    assert "production database write is not authorized; disposable-test-mode is required" in text
