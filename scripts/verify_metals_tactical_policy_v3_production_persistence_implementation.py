from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_production_persistence_authorization.json"
MIGRATION_PATH = ROOT / "foundation" / "import_engine" / "sql" / "009_metals_tactical_state_persistence.sql"
IMPORTER_PATH = ROOT / "scripts" / "persist_metals_tactical_policy_v3_current_state.py"

EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"


def main() -> int:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    if auth.get("authorization_id") != "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-AUTHORIZATION-1":
        raise RuntimeError("unexpected implementation authorization")
    storage = auth.get("authorized_storage", {})
    if storage.get("schema_migration_authorized") is not True:
        raise RuntimeError("schema migration not authorized")
    if storage.get("persistence_implementation_authorized") is not True:
        raise RuntimeError("persistence implementation not authorized")
    if storage.get("production_database_write_authorized") is not False:
        raise RuntimeError("production database write unexpectedly authorized")

    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    required_sql = [
        "CREATE TABLE IF NOT EXISTS metals_tactical_state_history",
        "CREATE OR REPLACE VIEW metals_tactical_state_current",
        "ROW_NUMBER() OVER",
        "PARTITION BY lower(universal_asset_id)",
        "source_state_sha256 VARCHAR NOT NULL",
        "source_materialization_manifest_sha256 VARCHAR NOT NULL",
        "_import_id VARCHAR NOT NULL",
        "_package_id VARCHAR NOT NULL",
        "_source_platform VARCHAR NOT NULL",
        "_source_filename VARCHAR NOT NULL",
        "_source_row_number BIGINT NOT NULL",
        "_manifest_sha256 VARCHAR NOT NULL",
        "_imported_at_utc TIMESTAMP NOT NULL",
    ]
    for fragment in required_sql:
        if fragment not in sql:
            raise RuntimeError(f"migration missing required fragment: {fragment}")
    forbidden_sql = ["INSERT OR REPLACE", "DELETE FROM metals_tactical_state_history", "UPDATE metals_tactical_state_history"]
    for fragment in forbidden_sql:
        if fragment in sql.upper():
            raise RuntimeError(f"migration contains forbidden history mutation: {fragment}")

    importer_text = IMPORTER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(importer_text)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    for forbidden in ("requests", "yfinance", "sqlalchemy"):
        if forbidden in imports:
            raise RuntimeError(f"persistence importer must not import {forbidden}")
    if "duckdb" not in imports:
        raise RuntimeError("persistence importer must use DuckDB")

    required_importer_fragments = [
        EXPECTED_STATE_SHA,
        EXPECTED_MANIFEST_SHA,
        "BEGIN TRANSACTION",
        "ROLLBACK",
        "COMMIT",
        "duplicate exact tactical-state import already exists",
        "postwrite history readback row count mismatch",
        "postwrite current view must return exactly 11 rows",
        "production database write is not authorized; disposable-test-mode is required",
        "--production-write-authorization",
        "--disposable-test-mode",
        "INSERT INTO metals_tactical_state_history",
    ]
    for fragment in required_importer_fragments:
        if fragment not in importer_text:
            raise RuntimeError(f"importer missing governed control: {fragment}")
    for forbidden in ("INSERT OR REPLACE", "DELETE FROM metals_tactical_state_history", "UPDATE metals_tactical_state_history"):
        if forbidden in importer_text.upper():
            raise RuntimeError(f"importer contains forbidden history mutation: {forbidden}")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "implementation_id": "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-IMPLEMENTATION-1",
        "history_table": "metals_tactical_state_history",
        "current_view": "metals_tactical_state_current",
        "source_state_sha256": EXPECTED_STATE_SHA,
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA,
        "schema_migration_implemented": True,
        "persistence_importer_implemented": True,
        "append_only_controls_implemented": True,
        "rollback_controls_implemented": True,
        "duplicate_exact_import_fail_closed_implemented": True,
        "production_database_write_authorized": False,
        "next_decision": "CERTIFY_METALS_TACTICAL_POLICY_V3_PRODUCTION_PERSISTENCE_IMPLEMENTATION",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
