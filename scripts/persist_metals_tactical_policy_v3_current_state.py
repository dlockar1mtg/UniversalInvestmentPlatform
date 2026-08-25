from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_production_persistence_authorization.json"
MIGRATION_PATH = ROOT / "foundation" / "import_engine" / "sql" / "009_metals_tactical_state_persistence.sql"

EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
EXPECTED_AS_OF_DATE = "2026-08-21"
EXPECTED_ROW_COUNT = 11
EXPECTED_OPPORTUNITY_COUNT = 10
EXPECTED_REFERENCE_COUNT = 1
EXPECTED_TICKERS = ["BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]
EXPECTED_PRICE_SEMANTICS = "UNADJUSTED_CLOSE"
EXPECTED_CLASSIFIER = "METALS-V3-REGIME-CANDIDATE-RULES-1"
EXPECTED_MAPPING = "METALS-V3-ACTION-MAPPING-1"
IMPORT_ID = "METALS-V3-TACTICAL-STATE-2026-08-21-00ea9954ead2"
PACKAGE_ID = "METALS-TACTICAL-POLICY-V3-CURRENT-STATE-MATERIALIZATION-1"
SOURCE_FILENAME = "metals_v3_current_state.jsonl"

FEATURE_FIELDS = [
    "return_1m_pct",
    "return_3m_pct",
    "return_6m_pct",
    "distance_ma50_pct",
    "distance_ma200_pct",
    "current_drawdown_pct",
    "realized_volatility_3m_pct",
    "trend_slope",
    "return_dispersion",
    "volatility_change",
    "drawdown_recovery_rate",
    "distance_from_recent_extreme",
    "short_vs_long_momentum_spread",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_source_row_number"] = line_number
            rows.append(row)
    return rows


def validate_authority(auth: dict[str, Any]) -> None:
    if auth.get("authorization_id") != "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-AUTHORIZATION-1":
        raise RuntimeError("unexpected production-persistence implementation authorization")
    if auth.get("authorization_decision") != "AUTHORIZE_BOUNDED_METALS_V3_PRODUCTION_PERSISTENCE_IMPLEMENTATION":
        raise RuntimeError("persistence implementation is not authorized")
    storage = auth.get("authorized_storage", {})
    if storage.get("schema_migration_authorized") is not True:
        raise RuntimeError("schema migration is not authorized")
    if storage.get("persistence_implementation_authorized") is not True:
        raise RuntimeError("persistence implementation is not authorized")
    if storage.get("production_database_write_authorized") is not False:
        raise RuntimeError("unexpected production write authority in implementation authorization")


def validate_source(state_path: Path, manifest_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if sha256_file(state_path) != EXPECTED_STATE_SHA:
        raise RuntimeError("certified state artifact SHA-256 mismatch")
    if sha256_file(manifest_path) != EXPECTED_MANIFEST_SHA:
        raise RuntimeError("certified materialization manifest SHA-256 mismatch")

    manifest = load_json(manifest_path)
    if manifest.get("materialization_id") != PACKAGE_ID:
        raise RuntimeError("unexpected materialization ID")
    if manifest.get("state_sha256") != EXPECTED_STATE_SHA:
        raise RuntimeError("manifest does not bind governed state SHA-256")
    if manifest.get("as_of_date") != EXPECTED_AS_OF_DATE:
        raise RuntimeError("unexpected materialization as-of date")
    if int(manifest.get("row_count", -1)) != EXPECTED_ROW_COUNT:
        raise RuntimeError("unexpected materialization row count")
    if int(manifest.get("opportunity_row_count", -1)) != EXPECTED_OPPORTUNITY_COUNT:
        raise RuntimeError("unexpected opportunity row count")
    if int(manifest.get("reference_control_row_count", -1)) != EXPECTED_REFERENCE_COUNT:
        raise RuntimeError("unexpected reference-control row count")
    if manifest.get("price_semantics") != EXPECTED_PRICE_SEMANTICS:
        raise RuntimeError("unexpected price semantics")
    if manifest.get("classifier_rule_version") != EXPECTED_CLASSIFIER:
        raise RuntimeError("unexpected classifier version")
    if manifest.get("action_mapping_version") != EXPECTED_MAPPING:
        raise RuntimeError("unexpected action mapping version")

    rows = load_rows(state_path)
    if len(rows) != EXPECTED_ROW_COUNT:
        raise RuntimeError("state artifact must contain exactly 11 rows")
    tickers = sorted(str(row.get("ticker", "")).upper() for row in rows)
    if tickers != EXPECTED_TICKERS:
        raise RuntimeError("governed tactical-state ticker universe changed")
    if sum(bool(row.get("is_reference_control")) for row in rows) != EXPECTED_REFERENCE_COUNT:
        raise RuntimeError("unexpected reference-control count in state rows")
    if sum(not bool(row.get("is_reference_control")) for row in rows) != EXPECTED_OPPORTUNITY_COUNT:
        raise RuntimeError("unexpected opportunity count in state rows")

    for row in rows:
        if row.get("as_of_date") != EXPECTED_AS_OF_DATE:
            raise RuntimeError("state row as-of date changed")
        if row.get("price_semantics") != EXPECTED_PRICE_SEMANTICS:
            raise RuntimeError("state row price semantics changed")
        if row.get("classifier_rule_version") != EXPECTED_CLASSIFIER:
            raise RuntimeError("state row classifier version changed")
        if row.get("action_mapping_version") != EXPECTED_MAPPING:
            raise RuntimeError("state row action mapping version changed")
        if row.get("source_package_id") != "metals-price-history-20260824":
            raise RuntimeError("state row source package changed")
        if row.get("ticker") == "BIL":
            if row.get("is_reference_control") is not True:
                raise RuntimeError("BIL must remain reference control")
            if row.get("state_available") is not False:
                raise RuntimeError("BIL state must remain unavailable")
        elif row.get("is_reference_control") is not False:
            raise RuntimeError("opportunity row unexpectedly marked reference control")
    return rows, manifest


def canonical_source_row(row: dict[str, Any]) -> str:
    payload = {k: v for k, v in row.items() if k != "_source_row_number"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def persist(database: Path, state_path: Path, manifest_path: Path, imported_at_utc: datetime) -> dict[str, Any]:
    auth = load_json(AUTH_PATH)
    validate_authority(auth)
    rows, _ = validate_source(state_path, manifest_path)
    migration_sql = MIGRATION_PATH.read_text(encoding="utf-8")

    if not database.exists():
        raise RuntimeError("target DuckDB does not exist")

    with duckdb.connect(str(database)) as connection:
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(migration_sql)

            duplicate_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM metals_tactical_state_history
                WHERE source_state_sha256 = ?
                  AND source_materialization_manifest_sha256 = ?
                """,
                [EXPECTED_STATE_SHA, EXPECTED_MANIFEST_SHA],
            ).fetchone()[0]
            if duplicate_count != 0:
                raise RuntimeError("duplicate exact tactical-state import already exists")

            insert_sql = """
                INSERT INTO metals_tactical_state_history (
                    universal_asset_id, ticker, as_of_date, candidate_regime, tactical_state,
                    classifier_rule_version, action_mapping_version, price_semantics,
                    source_package_id, state_available, state_reason, is_reference_control,
                    return_1m_pct, return_3m_pct, return_6m_pct, distance_ma50_pct,
                    distance_ma200_pct, current_drawdown_pct, realized_volatility_3m_pct,
                    trend_slope, return_dispersion, volatility_change, drawdown_recovery_rate,
                    distance_from_recent_extreme, short_vs_long_momentum_spread,
                    source_state_sha256, source_materialization_manifest_sha256,
                    source_row_json, _import_id, _package_id, _source_platform,
                    _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """

            values = []
            for row in rows:
                values.append((
                    row["asset_id"], row["ticker"], row["as_of_date"], row["candidate_regime"],
                    row["tactical_state"], row["classifier_rule_version"], row["action_mapping_version"],
                    row["price_semantics"], row["source_package_id"], bool(row["state_available"]),
                    row["state_reason"], bool(row["is_reference_control"]),
                    *[row.get(field) for field in FEATURE_FIELDS],
                    EXPECTED_STATE_SHA, EXPECTED_MANIFEST_SHA, canonical_source_row(row),
                    IMPORT_ID, PACKAGE_ID, "metals", SOURCE_FILENAME, row["_source_row_number"],
                    EXPECTED_MANIFEST_SHA, imported_at_utc,
                ))
            connection.executemany(insert_sql, values)

            persisted = connection.execute(
                """
                SELECT ticker, source_row_json
                FROM metals_tactical_state_history
                WHERE source_state_sha256 = ?
                  AND source_materialization_manifest_sha256 = ?
                ORDER BY ticker
                """,
                [EXPECTED_STATE_SHA, EXPECTED_MANIFEST_SHA],
            ).fetchall()
            if len(persisted) != EXPECTED_ROW_COUNT:
                raise RuntimeError("postwrite history readback row count mismatch")

            expected_by_ticker = {
                row["ticker"]: canonical_source_row(row)
                for row in rows
            }
            for ticker, source_row_json in persisted:
                if expected_by_ticker.get(ticker) != source_row_json:
                    raise RuntimeError(f"postwrite source-row readback mismatch for {ticker}")

            current_rows = connection.execute(
                """
                SELECT ticker, source_row_json
                FROM metals_tactical_state_current
                ORDER BY ticker
                """
            ).fetchall()
            if len(current_rows) != EXPECTED_ROW_COUNT:
                raise RuntimeError("postwrite current view must return exactly 11 rows")
            for ticker, source_row_json in current_rows:
                if expected_by_ticker.get(ticker) != source_row_json:
                    raise RuntimeError(f"postwrite current-view mismatch for {ticker}")

            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise

    return {
        "status": "PASS",
        "history_table": "metals_tactical_state_history",
        "current_view": "metals_tactical_state_current",
        "row_count": EXPECTED_ROW_COUNT,
        "opportunity_row_count": EXPECTED_OPPORTUNITY_COUNT,
        "reference_control_row_count": EXPECTED_REFERENCE_COUNT,
        "source_state_sha256": EXPECTED_STATE_SHA,
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA,
        "as_of_date": EXPECTED_AS_OF_DATE,
        "append_only": True,
        "duplicate_exact_import_must_fail_closed": True,
        "readback_exact_match": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--materialization-dir", required=True)
    parser.add_argument("--disposable-test-mode", action="store_true")
    parser.add_argument("--production-write-authorization")
    args = parser.parse_args()

    database = Path(args.database).resolve()
    materialization_dir = Path(args.materialization_dir).resolve()
    state_path = materialization_dir / SOURCE_FILENAME
    manifest_path = materialization_dir / "manifest.json"

    if not state_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("certified materialization files are missing")

    if args.disposable_test_mode:
        if args.production_write_authorization:
            raise RuntimeError("disposable test mode cannot also use production write authorization")
    else:
        if not args.production_write_authorization:
            raise RuntimeError("production database write is not authorized; disposable-test-mode is required")
        write_auth_path = Path(args.production_write_authorization).resolve()
        write_auth = load_json(write_auth_path)
        if write_auth.get("production_database_write_authorized") is not True:
            raise RuntimeError("provided production write authorization does not authorize database write")
        if write_auth.get("exact_state_sha256") != EXPECTED_STATE_SHA or write_auth.get("exact_manifest_sha256") != EXPECTED_MANIFEST_SHA:
            raise RuntimeError("production write authorization does not bind exact governed artifacts")

    result = persist(database, state_path, manifest_path, datetime.now(timezone.utc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
