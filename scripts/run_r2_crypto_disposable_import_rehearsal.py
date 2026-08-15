from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.import_engine.audit import apply_audit_registry_migration, synchronize_successful_import
from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.integrity import validate_package_integrity
from foundation.import_engine.loader import import_package
from foundation.import_engine.package import discover_package
from foundation.integrations.crypto.manual_production import validate_delivery

EXPECTED_COUNTS = {
    "asset_master": 6,
    "forecasts": 132,
    "platform_status": 1,
    "portfolio_positions": 0,
    "recommendations": 6,
    "risk_metrics": 6,
}
EXPECTED_IMPORTED_ROWS = sum(EXPECTED_COUNTS.values())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def load_env_file(path: Path, env: dict[str, str]) -> dict[str, bool]:
    present = path.is_file()
    if present:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in env:
                env[key] = value
    return {
        "source_env_present": present,
        "fred_api_key_available": bool(env.get("FRED_API_KEY", "").strip()),
        "coingecko_api_key_available": bool(env.get("COINGECKO_API_KEY", "").strip()),
        "coingecko_pro_api_key_available": bool(env.get("COINGECKO_PRO_API_KEY", "").strip()),
    }


def run_checked(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "Command failed: " + " ".join(command) + "\nSTDOUT:\n" + completed.stdout[-8000:] + "\nSTDERR:\n" + completed.stderr[-8000:]
        )
    return completed


def query_count(conn: duckdb.DuckDBPyConnection, table: str, package_id: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE _package_id = ?", [package_id]).fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a fresh Crypto pipeline on a disposable database and transactionally import its delivery into a disposable UIP database.")
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--source-repo", type=Path, required=True, help="Original Crypto repository containing the recovered database and .env")
    parser.add_argument("--crypto-code-root", type=Path, required=True, help="Crypto recovery worktree containing the governed R2 code")
    parser.add_argument(
        "--evidence-output",
        type=Path,
        default=ROOT / "docs" / "project_control" / "generated" / "r2_refreshed_data_rehearsal" / "crypto_r2_rehearsal_evidence.json",
    )
    args = parser.parse_args()

    source_db = args.source_database.resolve()
    source_repo = args.source_repo.resolve()
    crypto_code = args.crypto_code_root.resolve()
    evidence_output = args.evidence_output.resolve()

    if not source_db.is_file():
        raise RuntimeError(f"Source Crypto database missing: {source_db}")
    if not crypto_code.is_dir():
        raise RuntimeError(f"Crypto recovery code root missing: {crypto_code}")

    source_hash_before = sha256(source_db)
    source_size_before = source_db.stat().st_size

    env = os.environ.copy()
    env_state = load_env_file(source_repo / ".env", env)
    if not env_state["fred_api_key_available"]:
        raise RuntimeError("Recovered FRED configuration is unavailable; refusing fresh Crypto R2 rehearsal.")

    with tempfile.TemporaryDirectory(prefix="uip-r2-crypto-") as temp_name:
        temp_root = Path(temp_name)
        crypto_db = temp_root / "crypto_intelligence.duckdb"
        production_root = temp_root / "production_runs"
        delivery_root = temp_root / "uip_delivery"
        shutil.copy2(source_db, crypto_db)

        env["CRYPTO_DATABASE_PATH"] = str(crypto_db)
        env.pop("CRYPTO_PRODUCTION_RUN_ID", None)
        env.pop("CRYPTO_PRODUCTION_STAGE", None)
        env.pop("CRYPTO_PRODUCTION_MODULE", None)

        pipeline = run_checked(
            [
                sys.executable,
                str(crypto_code / "scripts" / "run_crypto_production_pipeline.py"),
                "--database",
                str(crypto_db),
                "--output-root",
                str(production_root),
            ],
            cwd=crypto_code,
            env=env,
        )

        summaries = sorted(production_root.glob("*/run_summary.json"))
        if len(summaries) != 1:
            raise RuntimeError(f"Expected exactly one fresh Crypto run summary, found {len(summaries)}")
        run_summary_path = summaries[0]
        run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
        if run_summary.get("status") != "PASS":
            raise RuntimeError("Fresh Crypto production run did not PASS.")
        if run_summary.get("full_refresh") is not False:
            raise RuntimeError("Crypto R2 rehearsal unexpectedly used full refresh.")
        failed_modules = [m for m in run_summary.get("module_results", []) if m.get("status") != "PASS"]
        if failed_modules:
            raise RuntimeError(f"Crypto production has failed modules: {failed_modules}")
        if len(run_summary.get("module_results", [])) != 43:
            raise RuntimeError("Crypto production did not record all 43 active modules.")

        export = run_summary.get("universal_export", {})
        if export.get("status") != "PASS" or export.get("dataset_counts") != EXPECTED_COUNTS:
            raise RuntimeError(f"Unexpected Crypto universal export: {export}")

        run_checked(
            [
                sys.executable,
                str(crypto_code / "scripts" / "prepare_crypto_uip_delivery.py"),
                "--run-summary",
                str(run_summary_path),
                "--output-root",
                str(delivery_root),
            ],
            cwd=crypto_code,
            env=env,
        )

        latest_pointer = delivery_root / "latest.json"
        manifest, delivery_dir = validate_delivery(latest_pointer)
        package_summary = json.loads((delivery_dir / "package_summary.json").read_text(encoding="utf-8"))
        if package_summary.get("dataset_counts") != EXPECTED_COUNTS:
            raise RuntimeError("Crypto delivery dataset counts do not match the fresh export.")

        disposable_uip_db = temp_root / "universal_investment.duckdb"
        config = ImportEngineConfig(
            repository_root=ROOT,
            database_path=disposable_uip_db,
            schema_root=ROOT / "schemas" / "v1" / "csv",
            integration_root=temp_root / "integration",
            validation_root=temp_root / "validation",
        )
        initialize_database(config)
        apply_audit_registry_migration(config)
        package = discover_package(delivery_dir)
        validation = validate_package_integrity(package)
        if not validation.passed:
            raise RuntimeError(f"Crypto package integrity failed with {validation.error_count} error(s).")

        imported = import_package(config, delivery_dir)
        synchronize_successful_import(config, import_id=imported.import_id)
        if imported.imported_row_count != EXPECTED_IMPORTED_ROWS:
            raise RuntimeError(
                f"Expected {EXPECTED_IMPORTED_ROWS} imported rows, got {imported.imported_row_count}."
            )

        conn = duckdb.connect(str(disposable_uip_db), read_only=True)
        try:
            history_counts = {
                "asset_master": query_count(conn, "asset_master_history", package.identity.package_id),
                "forecasts": query_count(conn, "forecasts_history", package.identity.package_id),
                "platform_status": query_count(conn, "platform_status_history", package.identity.package_id),
                "portfolio_positions": query_count(conn, "portfolio_positions_history", package.identity.package_id),
                "recommendations": query_count(conn, "recommendations_history", package.identity.package_id),
                "risk_metrics": query_count(conn, "risk_metrics_history", package.identity.package_id),
            }
        finally:
            conn.close()
        if history_counts != EXPECTED_COUNTS:
            raise RuntimeError(f"Disposable UIP history reconciliation failed: {history_counts}")

        source_hash_after = sha256(source_db)
        source_size_after = source_db.stat().st_size
        source_unchanged = source_hash_before == source_hash_after and source_size_before == source_size_after
        if not source_unchanged:
            raise RuntimeError("Source Crypto production database changed during disposable UIP rehearsal.")

        payload = {
            "status": "UIP_R2_CRYPTO_DISPOSABLE_IMPORT_REHEARSAL_PASS",
            "source_domain": "crypto",
            "source_repository": "dlockar1mtg/CryptoIntelligencePlatform",
            "source_commit_or_version": "951ca1111ef844a651eb6e12299441252ef5f56b",
            "crypto_recovery_branch": "phase-r2-crypto-recovery",
            "fresh_run_id": str(run_summary.get("run_id", "")),
            "full_refresh": False,
            "source_database_sha256": source_hash_before,
            "source_database_unchanged": source_unchanged,
            "source_env_present": env_state["source_env_present"],
            "fred_api_key_available": env_state["fred_api_key_available"],
            "coingecko_api_key_available": env_state["coingecko_api_key_available"],
            "coingecko_pro_api_key_available": env_state["coingecko_pro_api_key_available"],
            "module_count": len(run_summary.get("module_results", [])),
            "failed_modules": [],
            "universal_export": export,
            "uip_delivery_contract": manifest.get("delivery_contract"),
            "uip_delivery_status": manifest.get("status"),
            "package_id": package.identity.package_id,
            "uip_import_id": imported.import_id,
            "uip_import_status": "IMPORTED",
            "uip_imported_rows": imported.imported_row_count,
            "history_counts": history_counts,
            "native_semantics_reinterpreted": False,
            "cross_asset_rank_created": False,
            "automatic_purchase_execution_created": False,
            "production_uip_database_modified": False,
            "next_gate": "R2_CLOSEOUT_AND_R3_OUTPUT_RATIONALITY_REVIEW",
        }

        evidence_output.parent.mkdir(parents=True, exist_ok=True)
        evidence_output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        print("UIP_R2_CRYPTO_DISPOSABLE_IMPORT_REHEARSAL=PASS")
        print(f"EVIDENCE_OUTPUT={evidence_output}")
        print("SOURCE_DATABASE_UNCHANGED=TRUE")
        print("PRODUCTION_UIP_DATABASE_MODIFIED=FALSE")
        print("NEXT_GATE=R2_CLOSEOUT_AND_R3_OUTPUT_RATIONALITY_REVIEW")
        if pipeline.stdout:
            print("CRYPTO_PIPELINE_FINAL_OUTPUT=" + pipeline.stdout[-2000:].replace("\n", " | "))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
