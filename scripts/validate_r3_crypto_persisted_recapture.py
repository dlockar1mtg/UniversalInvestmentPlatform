from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_ROOT = ROOT / "docs" / "project_control" / "generated" / "r3_output_rationality_review" / "crypto_persisted_recapture"
EXPECTED_SOURCE_COMMIT = "951ca1111ef844a651eb6e12299441252ef5f56b"
EXPECTED_COUNTS = {
    "asset_master": 6,
    "forecasts": 132,
    "platform_status": 1,
    "portfolio_positions": 0,
    "recommendations": 6,
    "risk_metrics": 6,
}
REQUIRED_FILES = {
    "asset_master.csv",
    "export_manifest.csv",
    "forecasts.csv",
    "package_summary.json",
    "platform_status.csv",
    "portfolio_positions.csv",
    "recommendations.csv",
    "risk_metrics.csv",
    "validation_report.json",
    "run_summary.json",
}
COUNT_FILE_MAP = {
    "asset_master": "asset_master.csv",
    "forecasts": "forecasts.csv",
    "platform_status": "platform_status.csv",
    "portfolio_positions": "portfolio_positions.csv",
    "recommendations": "recommendations.csv",
    "risk_metrics": "risk_metrics.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def read_csv_header_and_count(path: Path) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            raise RuntimeError(f"CSV is empty and has no header: {path}")
        count = sum(1 for _ in reader)
    return header, count


def main() -> int:
    if not CAPTURE_ROOT.is_dir():
        raise RuntimeError(f"Missing Crypto persisted recapture root: {CAPTURE_ROOT}")

    captures = sorted(p for p in CAPTURE_ROOT.iterdir() if p.is_dir())
    if len(captures) != 1:
        raise RuntimeError(f"Expected exactly one governed Crypto recapture directory, found {len(captures)}")
    capture = captures[0]

    manifest_path = capture / "r3_crypto_capture_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Missing recapture manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("status") != "UIP_R3_CRYPTO_PERSISTED_RECAPTURE_PASS":
        raise RuntimeError("Crypto recapture manifest status is not PASS.")
    if manifest.get("authority_mode") != "R3_PERSISTED_RECAPTURE":
        raise RuntimeError("Crypto recapture authority mode is not governed R3_PERSISTED_RECAPTURE.")
    if manifest.get("is_exact_r2_output") is not False:
        raise RuntimeError("Crypto recapture is incorrectly labeled as exact R2 output.")
    if manifest.get("source_commit_or_version") != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError("Crypto recapture source commit differs from certified native authority.")
    if manifest.get("source_database_unchanged") is not True:
        raise RuntimeError("Crypto source database unchanged proof is missing or false.")
    if manifest.get("full_refresh") is not False:
        raise RuntimeError("Crypto recapture did not use the governed incremental refresh path.")
    if manifest.get("module_count") != 43 or manifest.get("failed_modules") != []:
        raise RuntimeError("Crypto recapture module execution is incomplete or failed.")
    if manifest.get("dataset_counts") != EXPECTED_COUNTS:
        raise RuntimeError(f"Unexpected Crypto dataset counts: {manifest.get('dataset_counts')}")
    if not str(manifest.get("governed_gap", "")).strip():
        raise RuntimeError("Crypto exact-prior-row governed gap is not recorded.")

    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list):
        raise RuntimeError("Crypto recapture manifest files ledger is missing.")
    ledger = {str(item.get("name")): item for item in manifest_files if isinstance(item, dict)}
    if set(ledger) != REQUIRED_FILES:
        raise RuntimeError(f"Crypto recapture file ledger mismatch. Expected {sorted(REQUIRED_FILES)}, got {sorted(ledger)}")

    actual_files = {p.name for p in capture.iterdir() if p.is_file()}
    expected_actual = REQUIRED_FILES | {"r3_crypto_capture_manifest.json"}
    if actual_files != expected_actual:
        raise RuntimeError(f"Crypto recapture directory file set mismatch. Expected {sorted(expected_actual)}, got {sorted(actual_files)}")

    integrity_results = {}
    for name in sorted(REQUIRED_FILES):
        path = capture / name
        entry = ledger[name]
        actual_hash = sha256(path)
        actual_size = path.stat().st_size
        expected_hash = str(entry.get("sha256", "")).lower()
        expected_size = int(entry.get("size_bytes", -1))
        if actual_hash != expected_hash:
            raise RuntimeError(f"Hash mismatch for {name}: expected {expected_hash}, got {actual_hash}")
        if actual_size != expected_size:
            raise RuntimeError(f"Size mismatch for {name}: expected {expected_size}, got {actual_size}")
        integrity_results[name] = {"sha256": actual_hash, "size_bytes": actual_size}

    schemas = {}
    row_counts = {}
    for dataset, filename in COUNT_FILE_MAP.items():
        header, count = read_csv_header_and_count(capture / filename)
        if count != EXPECTED_COUNTS[dataset]:
            raise RuntimeError(f"Row count mismatch for {dataset}: expected {EXPECTED_COUNTS[dataset]}, got {count}")
        if len(header) != len(set(header)):
            raise RuntimeError(f"Duplicate CSV column names in {filename}")
        if any(not str(column).strip() for column in header):
            raise RuntimeError(f"Blank CSV column name in {filename}")
        schemas[dataset] = header
        row_counts[dataset] = count

    package_summary = json.loads((capture / "package_summary.json").read_text(encoding="utf-8"))
    validation_report = json.loads((capture / "validation_report.json").read_text(encoding="utf-8"))
    run_summary = json.loads((capture / "run_summary.json").read_text(encoding="utf-8"))

    if run_summary.get("status") != "PASS":
        raise RuntimeError("Persisted run_summary status is not PASS.")
    if run_summary.get("full_refresh") is not False:
        raise RuntimeError("Persisted run_summary contradicts governed incremental refresh.")
    export = run_summary.get("universal_export", {})
    if export.get("status") != "PASS" or export.get("dataset_counts") != EXPECTED_COUNTS:
        raise RuntimeError("Persisted run_summary universal export does not reconcile to the manifest.")

    summary_counts = package_summary.get("dataset_counts")
    if summary_counts is not None and summary_counts != EXPECTED_COUNTS:
        raise RuntimeError(f"package_summary dataset counts do not reconcile: {summary_counts}")

    output = {
        "status": "UIP_R3_CRYPTO_PERSISTED_RECAPTURE_VALIDATION_PASS",
        "capture_directory": str(capture),
        "authority_mode": manifest["authority_mode"],
        "is_exact_r2_output": manifest["is_exact_r2_output"],
        "r2_prior_run_id": manifest.get("r2_prior_run_id"),
        "recapture_run_id": manifest.get("run_id"),
        "source_commit_or_version": manifest.get("source_commit_or_version"),
        "source_database_sha256": manifest.get("source_database_sha256"),
        "source_database_unchanged": manifest.get("source_database_unchanged"),
        "dataset_counts": row_counts,
        "schemas": schemas,
        "file_integrity_verified": True,
        "file_count_excluding_capture_manifest": len(REQUIRED_FILES),
        "governed_gap_preserved": True,
        "package_summary_parseable": isinstance(package_summary, dict),
        "validation_report_parseable": isinstance(validation_report, dict),
        "run_summary_reconciled": True,
        "cross_asset_ranking_created": False,
        "allocation_policy_created": False,
        "automatic_execution_created": False,
        "next_gate": "R3_CRYPTO_OUTPUT_RATIONALITY_REVIEW",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    print("UIP_R3_CRYPTO_PERSISTED_RECAPTURE_VALIDATION=PASS")
    print("NEXT_GATE=R3_CRYPTO_OUTPUT_RATIONALITY_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
