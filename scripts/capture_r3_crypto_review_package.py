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

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"
EXPECTED_COUNTS = {
    "asset_master": 6,
    "forecasts": 132,
    "platform_status": 1,
    "portfolio_positions": 0,
    "recommendations": 6,
    "risk_metrics": 6,
}


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


def git_head(repo: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Unable to resolve git HEAD for {repo}: {result.stderr}")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a durable Crypto R3 review package using the governed persisted-recapture exception.")
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--crypto-code-root", type=Path, required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "docs" / "project_control" / "generated" / "r3_output_rationality_review" / "crypto_persisted_recapture",
    )
    args = parser.parse_args()

    source_db = args.source_database.resolve()
    source_repo = args.source_repo.resolve()
    crypto_code = args.crypto_code_root.resolve()
    output_root = args.output_root.resolve()

    if not source_db.is_file():
        raise RuntimeError(f"Missing Crypto source database: {source_db}")
    if not crypto_code.is_dir():
        raise RuntimeError(f"Missing Crypto code root: {crypto_code}")

    source_commit = git_head(crypto_code)
    if source_commit != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError(f"Crypto code root is not at certified source commit {EXPECTED_SOURCE_COMMIT}; got {source_commit}")

    source_hash_before = sha256(source_db)
    source_size_before = source_db.stat().st_size

    env = os.environ.copy()
    env_state = load_env_file(source_repo / ".env", env)
    if not env_state["fred_api_key_available"]:
        raise RuntimeError("Recovered FRED configuration unavailable; refusing R3 Crypto recapture.")

    with tempfile.TemporaryDirectory(prefix="uip-r3-crypto-capture-") as temp_name:
        temp_root = Path(temp_name)
        crypto_db = temp_root / "crypto_intelligence.duckdb"
        production_root = temp_root / "production_runs"
        shutil.copy2(source_db, crypto_db)

        env["CRYPTO_DATABASE_PATH"] = str(crypto_db)
        env.pop("CRYPTO_PRODUCTION_RUN_ID", None)
        env.pop("CRYPTO_PRODUCTION_STAGE", None)
        env.pop("CRYPTO_PRODUCTION_MODULE", None)

        run_checked(
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
            raise RuntimeError(f"Expected one Crypto run summary, found {len(summaries)}")
        run_summary_path = summaries[0]
        run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))

        if run_summary.get("status") != "PASS":
            raise RuntimeError("Crypto persisted recapture production run did not PASS.")
        if run_summary.get("full_refresh") is not False:
            raise RuntimeError("Crypto persisted recapture unexpectedly used full refresh.")
        module_results = run_summary.get("module_results", [])
        failed = [m for m in module_results if m.get("status") != "PASS"]
        if failed or len(module_results) != 43:
            raise RuntimeError(f"Unexpected module results: count={len(module_results)} failed={failed}")

        export = run_summary.get("universal_export", {})
        if export.get("status") != "PASS" or export.get("dataset_counts") != EXPECTED_COUNTS:
            raise RuntimeError(f"Unexpected universal export: {export}")

        universal_package = Path(export.get("output_directory", ""))
        if not universal_package.is_dir():
            raise RuntimeError(f"Universal package missing: {universal_package}")

        run_id = str(run_summary.get("run_id", "")).strip()
        if not run_id:
            raise RuntimeError("Crypto recapture run_id missing.")

        target = output_root / run_id
        if target.exists():
            raise RuntimeError(f"Refusing to overwrite existing R3 Crypto capture: {target}")
        target.mkdir(parents=True, exist_ok=False)

        copied_files: list[dict[str, object]] = []
        for source in sorted(universal_package.iterdir()):
            if not source.is_file():
                continue
            destination = target / source.name
            shutil.copy2(source, destination)
            copied_files.append({
                "name": source.name,
                "sha256": sha256(destination),
                "size_bytes": destination.stat().st_size,
            })

        run_summary_copy = target / "run_summary.json"
        shutil.copy2(run_summary_path, run_summary_copy)
        copied_files.append({
            "name": "run_summary.json",
            "sha256": sha256(run_summary_copy),
            "size_bytes": run_summary_copy.stat().st_size,
        })

        source_hash_after = sha256(source_db)
        source_size_after = source_db.stat().st_size
        source_unchanged = source_hash_before == source_hash_after and source_size_before == source_size_after
        if not source_unchanged:
            raise RuntimeError("Source Crypto database changed during R3 persisted recapture.")

        manifest = {
            "status": "UIP_R3_CRYPTO_PERSISTED_RECAPTURE_PASS",
            "authority_mode": "R3_PERSISTED_RECAPTURE",
            "is_exact_r2_output": False,
            "r2_prior_run_id": "crypto-prod-20260815T122413Z-e7429e07",
            "source_repository": "dlockar1mtg/CryptoIntelligencePlatform",
            "source_commit_or_version": source_commit,
            "full_refresh": False,
            "source_database_sha256": source_hash_before,
            "source_database_unchanged": True,
            "source_env_present": env_state["source_env_present"],
            "fred_api_key_available": env_state["fred_api_key_available"],
            "coingecko_api_key_available": env_state["coingecko_api_key_available"],
            "coingecko_pro_api_key_available": env_state["coingecko_pro_api_key_available"],
            "run_id": run_id,
            "module_count": len(module_results),
            "failed_modules": [],
            "dataset_counts": EXPECTED_COUNTS,
            "files": copied_files,
            "governed_gap": "Exact row-level R2 Crypto package was not retained; exact row-to-row comparison against R2 is unavailable unless the original package is later recovered.",
            "next_gate": "R3_CRYPTO_OUTPUT_RATIONALITY_REVIEW",
        }
        manifest_path = target / "r3_crypto_capture_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        print(json.dumps(manifest, indent=2, sort_keys=True))
        print("UIP_R3_CRYPTO_PERSISTED_RECAPTURE=PASS")
        print(f"CAPTURE_DIRECTORY={target}")
        print("SOURCE_DATABASE_UNCHANGED=TRUE")
        print("IS_EXACT_R2_OUTPUT=FALSE")
        print("NEXT_GATE=R3_CRYPTO_OUTPUT_RATIONALITY_REVIEW")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
