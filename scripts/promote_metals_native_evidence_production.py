from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from rehearse_metals_native_evidence_promotion import MIGRATION, current_lineage, promote


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_counts(connection: duckdb.DuckDBPyConnection) -> dict[str, int]:
    return {
        "components": connection.execute("SELECT COUNT(*) FROM metals_forecast_model_component_current").fetchone()[0],
        "regimes": connection.execute("SELECT COUNT(*) FROM metals_regime_probability_current").fetchone()[0],
        "adjusted": connection.execute("SELECT COUNT(*) FROM metals_uncertainty_adjusted_view_current").fetchone()[0],
        "changes": connection.execute("SELECT COUNT(*) FROM metals_recommendation_change_current").fetchone()[0],
        "freshness": connection.execute("SELECT COUNT(*) FROM metals_data_freshness_current").fetchone()[0],
        "health": connection.execute("SELECT COUNT(*) FROM metals_platform_health_current").fetchone()[0],
    }


def package_counts(connection: duckdb.DuckDBPyConnection, package_id: str) -> dict[str, int]:
    return {
        "components": connection.execute("SELECT COUNT(*) FROM metals_forecast_model_component_current WHERE _package_id=?", [package_id]).fetchone()[0],
        "regimes": connection.execute("SELECT COUNT(*) FROM metals_regime_probability_current WHERE _package_id=?", [package_id]).fetchone()[0],
        "adjusted": connection.execute("SELECT COUNT(*) FROM metals_uncertainty_adjusted_view_current WHERE _package_id=?", [package_id]).fetchone()[0],
        "changes": connection.execute("SELECT COUNT(*) FROM metals_recommendation_change_current WHERE _package_id=?", [package_id]).fetchone()[0],
        "freshness": connection.execute("SELECT COUNT(*) FROM metals_data_freshness_current WHERE _package_id=?", [package_id]).fetchone()[0],
        "health": connection.execute("SELECT COUNT(*) FROM metals_platform_health_current WHERE _package_id=?", [package_id]).fetchone()[0],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote certified Metals-native supporting evidence into production UIP authority.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    args = parser.parse_args()

    before = sha256_file(args.database)
    if before.lower() != args.expected_sha256.lower():
        raise RuntimeError(f"Database SHA-256 mismatch: {before}")
    if not MIGRATION.is_file():
        raise FileNotFoundError(f"Migration missing: {MIGRATION}")
    if not (args.package_root / "package_summary.json").is_file():
        raise FileNotFoundError("Certified Metals package summary is missing.")

    args.backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = args.backup_root / f"universal_investment_pre_metals_native_promotion_{stamp}.duckdb"
    shutil.copy2(args.database, backup)
    backup_sha = sha256_file(backup)
    if backup_sha.lower() != before.lower():
        backup.unlink(missing_ok=True)
        raise RuntimeError("Backup checksum does not match authoritative database before mutation.")

    connection = duckdb.connect(str(args.database))
    try:
        connection.execute(MIGRATION.read_text(encoding="utf-8"))
        package_id, import_id, manifest = current_lineage(connection)
        summary = json.loads((args.package_root / "package_summary.json").read_text(encoding="utf-8"))
        source_package_id = str(summary.get("package_id", ""))
        if source_package_id != package_id:
            raise RuntimeError(f"Package ID mismatch: source={source_package_id} current={package_id}")

        existing = package_counts(connection, package_id)
        if any(existing.values()):
            expected = {"components": 64, "regimes": 12, "adjusted": 32, "changes": 10, "freshness": 21, "health": 1}
            if existing != expected:
                raise RuntimeError(f"Partial prior promotion detected for current package: {existing}")
            observed = current_counts(connection)
            mode = "NOOP_ALREADY_PROMOTED"
        else:
            connection.execute("BEGIN TRANSACTION")
            try:
                source_counts = promote(connection, args.package_root)
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
            observed = package_counts(connection, package_id)
            if observed != source_counts:
                raise RuntimeError(f"Production promotion count mismatch: source={source_counts} current={observed}")
            mode = "PRODUCTION_PROMOTION"
    finally:
        connection.close()

    after = sha256_file(args.database)
    if mode == "PRODUCTION_PROMOTION" and after.lower() == before.lower():
        raise RuntimeError("Production database hash did not change after authorized promotion.")
    if mode == "NOOP_ALREADY_PROMOTED" and after.lower() != before.lower():
        raise RuntimeError("Database changed during an idempotent no-op promotion check.")

    print(json.dumps({
        "status": "PASS",
        "mode": mode,
        "package_id": package_id,
        "import_id": import_id,
        "manifest_sha256": manifest,
        "database_sha256_before": before,
        "database_sha256_after": after,
        "backup_path": str(backup),
        "backup_sha256": backup_sha,
        "promoted_counts": observed,
        "automatic_execution_authorized": False,
        "next_decision": "VERIFY_AND_PUBLISH_METALS_TACTICAL_EVIDENCE",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
