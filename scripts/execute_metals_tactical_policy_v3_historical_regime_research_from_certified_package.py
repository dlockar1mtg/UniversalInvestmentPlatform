from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "execute_metals_tactical_policy_v3_historical_regime_research.py"

EXPECTED_HISTORY_SHA256 = "400aa5792533653eccf7bdfb3dd4b67fddb8f45ad138bda1a7d4ac1c1137bd62"
EXPECTED_COVERAGE_SHA256 = "26477acb7f50169980ea6c1ede73b6cfac7ffbc21b34273a1253f1ffa6b5f9f9"
EXPECTED_MANIFEST_SHA256 = "602521ce36c4f1cb0797dc29d932c803bd0e0a12c38652211c1cdd1cf32216dd"
EXPECTED_PACKAGE_ID = "metals-v2-validation-history-20191204-20230821"
EXPECTED_HISTORY_ROWS = 10274
EXPECTED_VEHICLES = 11
EXPECTED_OBSERVATIONS_PER_VEHICLE = 934


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_runner():
    spec = importlib.util.spec_from_file_location("metals_v3_regime_inner_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load governed historical regime research runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_package(package_dir: Path) -> tuple[Path, Path, Path]:
    history = package_dir / "metals_v2_validation_history.jsonl"
    coverage = package_dir / "coverage.json"
    manifest = package_dir / "manifest.json"
    for path in (history, coverage, manifest):
        if not path.is_file():
            raise RuntimeError(f"required certified V2 package artifact is missing: {path.name}")
    if sha256_file(history) != EXPECTED_HISTORY_SHA256:
        raise RuntimeError("certified V2 history SHA-256 mismatch")
    if sha256_file(coverage) != EXPECTED_COVERAGE_SHA256:
        raise RuntimeError("certified V2 coverage SHA-256 mismatch")
    if sha256_file(manifest) != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("certified V2 manifest SHA-256 mismatch")

    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_payload.get("package_id") != EXPECTED_PACKAGE_ID:
        raise RuntimeError("unexpected certified V2 package id")
    if manifest_payload.get("outcome_blind") is not True:
        raise RuntimeError("certified V2 package is not marked outcome blind")
    if int(manifest_payload.get("history_row_count", -1)) != EXPECTED_HISTORY_ROWS:
        raise RuntimeError("certified V2 package history row count changed")

    coverage_payload = json.loads(coverage.read_text(encoding="utf-8"))
    if int(coverage_payload.get("vehicle_count", -1)) != EXPECTED_VEHICLES:
        raise RuntimeError("certified V2 package vehicle count changed")
    if int(coverage_payload.get("common_observation_count", -1)) != EXPECTED_OBSERVATIONS_PER_VEHICLE:
        raise RuntimeError("certified V2 package common observation count changed")
    if int(coverage_payload.get("total_history_row_count", -1)) != EXPECTED_HISTORY_ROWS:
        raise RuntimeError("certified V2 coverage row count changed")
    return history, coverage, manifest


def normalize_history(history_jsonl: Path, normalized_csv: Path) -> None:
    required = (
        "asset_id",
        "ticker",
        "observation_date",
        "close_usd",
        "adjusted_close_usd",
        "source_provider",
        "package_id",
    )
    row_count = 0
    tickers: set[str] = set()
    seen: set[tuple[str, str]] = set()
    with normalized_csv.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["ticker", "observation_date", "close"])
        writer.writeheader()
        with history_jsonl.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    continue
                record = json.loads(raw_line)
                missing = [name for name in required if name not in record]
                if missing:
                    raise RuntimeError(f"certified history row missing fields: {missing}")
                ticker = str(record["ticker"]).strip().upper()
                date = str(record["observation_date"]).strip()
                asset_id = str(record["asset_id"]).strip()
                if asset_id != f"metals:vehicle:{ticker}":
                    raise RuntimeError("certified history asset/ticker identity mismatch")
                if record["package_id"] != EXPECTED_PACKAGE_ID:
                    raise RuntimeError("certified history row package id changed")
                if str(record["source_provider"]).strip().lower() != "yfinance":
                    raise RuntimeError("certified history source provider changed")
                close = float(record["close_usd"])
                if close <= 0:
                    raise RuntimeError("certified history contains nonpositive raw close")
                key = (ticker, date)
                if key in seen:
                    raise RuntimeError("duplicate ticker/date in certified V2 history")
                seen.add(key)
                tickers.add(ticker)
                writer.writerow({"ticker": ticker, "observation_date": date, "close": repr(close)})
                row_count += 1
    if row_count != EXPECTED_HISTORY_ROWS:
        raise RuntimeError(f"normalized history row count changed: {row_count}")
    if len(tickers) != EXPECTED_VEHICLES:
        raise RuntimeError(f"normalized history vehicle count changed: {len(tickers)}")
    if "BIL" not in tickers:
        raise RuntimeError("BIL reference/control missing from certified history")


def rebuild_manifest(output_dir: Path, source_history: Path, source_coverage: Path, source_manifest: Path) -> dict[str, object]:
    consumed_path = output_dir / "consumed_evidence_disclosure.json"
    consumed = json.loads(consumed_path.read_text(encoding="utf-8"))
    consumed.pop("source_history_csv", None)
    consumed["source_package_id"] = EXPECTED_PACKAGE_ID
    consumed["source_history_jsonl"] = str(source_history)
    consumed["source_history_sha256"] = EXPECTED_HISTORY_SHA256
    consumed["source_coverage_sha256"] = EXPECTED_COVERAGE_SHA256
    consumed["source_manifest_sha256"] = EXPECTED_MANIFEST_SHA256
    consumed["certified_source_package_unchanged"] = True
    write_json(consumed_path, consumed)

    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_package_id"] = EXPECTED_PACKAGE_ID
    manifest["source_history_sha256"] = EXPECTED_HISTORY_SHA256
    manifest["source_coverage_sha256"] = EXPECTED_COVERAGE_SHA256
    manifest["source_manifest_sha256"] = EXPECTED_MANIFEST_SHA256
    manifest["source_format"] = "CERTIFIED_JSONL_NORMALIZED_IN_EPHEMERAL_TEMPORARY_DIRECTORY"
    manifest["raw_close_field"] = "close_usd"
    manifest["adjusted_close_used_for_v3_features_or_outcomes"] = False
    manifest["output_files"] = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    package_dir = Path(args.package_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    history, coverage, manifest = validate_package(package_dir)

    with tempfile.TemporaryDirectory(prefix="uip_metals_v3_regime_") as temporary:
        normalized_csv = Path(temporary) / "certified_history_normalized.csv"
        normalize_history(history, normalized_csv)
        runner = load_runner()
        original_argv = sys.argv[:]
        captured = io.StringIO()
        try:
            sys.argv = [str(RUNNER_PATH), "--history-csv", str(normalized_csv), "--output-dir", str(output_dir)]
            with redirect_stdout(captured):
                rc = int(runner.main())
        finally:
            sys.argv = original_argv
        if rc != 0:
            raise RuntimeError(f"governed inner regime research runner failed with exit code {rc}")

    final_manifest = rebuild_manifest(output_dir, history, coverage, manifest)
    print(json.dumps({
        "status": "PASS",
        "execution_id": final_manifest["execution_id"],
        "research_role": final_manifest["research_role"],
        "source_package_id": final_manifest["source_package_id"],
        "source_history_sha256": final_manifest["source_history_sha256"],
        "source_coverage_sha256": final_manifest["source_coverage_sha256"],
        "source_manifest_sha256": final_manifest["source_manifest_sha256"],
        "raw_close_field": final_manifest["raw_close_field"],
        "adjusted_close_used_for_v3_features_or_outcomes": final_manifest["adjusted_close_used_for_v3_features_or_outcomes"],
        "history_row_count": final_manifest["history_row_count"],
        "vehicle_count": final_manifest["vehicle_count"],
        "observations_per_vehicle": final_manifest["observations_per_vehicle"],
        "label_ledger_row_count": final_manifest["label_ledger_row_count"],
        "label_ledger_sha256": final_manifest["label_ledger_sha256"],
        "directional_regime_minimum_support_gate_met": final_manifest["directional_regime_minimum_support_gate_met"],
        "regime_definition_authorized": False,
        "tactical_posture_authorized": False,
        "unseen_validation_claim_authorized": False,
        "output_dir": str(output_dir),
        "next_decision": final_manifest["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
