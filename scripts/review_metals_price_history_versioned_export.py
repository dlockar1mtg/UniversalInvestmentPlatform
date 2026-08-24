from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_PATH = ROOT / "config" / "presentation" / "metals_price_history_versioned_export_review.json"
TICKERS = ("BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise RuntimeError(f"blank JSONL row in {path.name} at line {line_number}")
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise RuntimeError(f"non-object JSONL row in {path.name} at line {line_number}")
            rows.append(payload)
    return rows


def require_finite_positive(value: object, label: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise RuntimeError(f"invalid positive value for {label}")
    return number


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-PRICE-HISTORY-VERSIONED-EXPORT-REVIEW-1":
        raise RuntimeError("unexpected Metals price/history export review contract")
    controls = contract.get("controls") or {}
    if controls.get("read_only_review") is not True:
        raise RuntimeError("export review is not governed read-only")
    for key in (
        "native_source_query_authorized",
        "export_execution_authorized",
        "production_database_write_authorized",
        "presentation_activation_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "tactical_posture_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited review control changed unexpectedly: {key}")

    package_dir = Path(parse_args().package_dir).resolve()
    current_path = package_dir / "metals_current_price.jsonl"
    history_path = package_dir / "metals_price_history.jsonl"
    manifest_path = package_dir / "manifest.json"
    for path in (current_path, history_path, manifest_path):
        if not path.is_file():
            raise RuntimeError(f"required package artifact is missing: {path}")

    actual_current_sha = sha256_file(current_path)
    actual_history_sha = sha256_file(history_path)
    actual_manifest_sha = sha256_file(manifest_path)
    expected_hashes = {
        "current": str(contract["expected_current_price_sha256"]),
        "history": str(contract["expected_price_history_sha256"]),
        "manifest": str(contract["expected_manifest_sha256"]),
    }
    if actual_current_sha != expected_hashes["current"]:
        raise RuntimeError("current-price package hash changed")
    if actual_history_sha != expected_hashes["history"]:
        raise RuntimeError("price-history package hash changed")
    if actual_manifest_sha != expected_hashes["manifest"]:
        raise RuntimeError("manifest package hash changed")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("package_id") != contract["package_id"]:
        raise RuntimeError("package ID changed")
    if manifest.get("source_authority") != contract["source_authority"]:
        raise RuntimeError("source authority changed")
    if manifest.get("source_run_id") != contract["source_run_id"]:
        raise RuntimeError("source run ID changed")
    if manifest.get("source_system") != contract["source_system"]:
        raise RuntimeError("source system changed")
    if int(manifest.get("vehicle_count", -1)) != int(contract["expected_vehicle_count"]):
        raise RuntimeError("manifest vehicle count changed")
    if int(manifest.get("history_point_count", -1)) != int(contract["expected_history_point_count"]):
        raise RuntimeError("manifest history point count changed")

    files = manifest.get("files") or {}
    current_manifest = files.get(current_path.name) or {}
    history_manifest = files.get(history_path.name) or {}
    if current_manifest.get("sha256") != actual_current_sha or int(current_manifest.get("record_count", -1)) != int(contract["expected_current_price_record_count"]):
        raise RuntimeError("current-price manifest entry does not reconcile")
    if history_manifest.get("sha256") != actual_history_sha or int(history_manifest.get("record_count", -1)) != int(contract["expected_history_point_count"]):
        raise RuntimeError("price-history manifest entry does not reconcile")

    current_rows = load_jsonl(current_path)
    history_rows = load_jsonl(history_path)
    if len(current_rows) != int(contract["expected_current_price_record_count"]):
        raise RuntimeError("current-price row count changed")
    if len(history_rows) != int(contract["expected_history_point_count"]):
        raise RuntimeError("history row count changed")

    observed_current_tickers = sorted(str(row.get("ticker")) for row in current_rows)
    if observed_current_tickers != sorted(TICKERS):
        raise RuntimeError("current-price ticker population changed")

    history_counts: Counter[str] = Counter()
    history_dates: dict[str, list[str]] = defaultdict(list)
    history_latest: dict[str, dict[str, object]] = {}
    seen_keys: set[tuple[str, str]] = set()
    for row in history_rows:
        ticker = str(row.get("ticker"))
        if ticker not in TICKERS:
            raise RuntimeError(f"unexpected history ticker: {ticker}")
        date_text = str(row.get("observation_date"))
        key = (ticker, date_text)
        if key in seen_keys:
            raise RuntimeError(f"duplicate history key: {ticker} {date_text}")
        seen_keys.add(key)
        if row.get("asset_id") != f"metals:vehicle:{ticker}":
            raise RuntimeError(f"asset ID mismatch for {ticker} {date_text}")
        require_finite_positive(row.get("close_usd"), f"{ticker} close {date_text}")
        adjusted = row.get("adjusted_close_usd")
        if adjusted is not None:
            require_finite_positive(adjusted, f"{ticker} adjusted close {date_text}")
        volume = row.get("volume")
        if volume is not None:
            volume_number = float(volume)
            if not math.isfinite(volume_number) or volume_number < 0:
                raise RuntimeError(f"invalid volume for {ticker} {date_text}")
        if row.get("source_authority") != contract["source_authority"] or row.get("source_run_id") != contract["source_run_id"] or row.get("source_system") != contract["source_system"]:
            raise RuntimeError(f"history lineage changed for {ticker} {date_text}")
        history_counts[ticker] += 1
        history_dates[ticker].append(date_text)
        history_latest[ticker] = row

    if sorted(history_counts) != sorted(TICKERS):
        raise RuntimeError("history ticker population changed")
    if sum(history_counts.values()) != int(contract["expected_history_point_count"]):
        raise RuntimeError("history count reconciliation failed")

    current_by_ticker = {str(row["ticker"]): row for row in current_rows}
    coverage: list[dict[str, object]] = []
    for ticker in sorted(TICKERS):
        row = current_by_ticker[ticker]
        if row.get("asset_id") != f"metals:vehicle:{ticker}":
            raise RuntimeError(f"current-price asset ID mismatch for {ticker}")
        current_price = require_finite_positive(row.get("current_price_usd"), f"{ticker} current price")
        if row.get("source_authority") != contract["source_authority"] or row.get("source_run_id") != contract["source_run_id"] or row.get("source_system") != contract["source_system"]:
            raise RuntimeError(f"current-price lineage changed for {ticker}")
        latest = history_latest[ticker]
        effective_latest = float(latest["adjusted_close_usd"] if latest.get("adjusted_close_usd") is not None else latest["close_usd"])
        if str(row.get("observation_date")) != str(latest.get("observation_date")):
            raise RuntimeError(f"current-price date does not match latest history for {ticker}")
        if current_price != effective_latest:
            raise RuntimeError(f"current-price value does not match latest history for {ticker}")
        coverage.append({
            "ticker": ticker,
            "history_count": history_counts[ticker],
            "min_date": min(history_dates[ticker]),
            "max_date": max(history_dates[ticker]),
            "current_price_usd": current_price,
        })

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": contract["contract_id"],
        "package_id": contract["package_id"],
        "source_authority": contract["source_authority"],
        "source_run_id": contract["source_run_id"],
        "vehicle_count": len(current_rows),
        "current_price_record_count": len(current_rows),
        "history_point_count": len(history_rows),
        "current_price_sha256": actual_current_sha,
        "price_history_sha256": actual_history_sha,
        "manifest_sha256": actual_manifest_sha,
        "coverage": coverage,
        "package_integrity_verified": True,
        "current_price_latest_history_reconciliation_verified": True,
        "native_source_query_executed": False,
        "export_execution_executed": False,
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
