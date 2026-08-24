from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_validation_history_package_review.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    args = parser.parse_args()

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    package = contract["package_contract"]
    controls = contract["controls"]
    package_dir = Path(args.package_dir)

    history_path = package_dir / package["history_filename"]
    coverage_path = package_dir / package["coverage_filename"]
    manifest_path = package_dir / package["manifest_filename"]

    for path in (history_path, coverage_path, manifest_path):
        if not path.is_file():
            raise RuntimeError(f"Required package artifact is missing: {path}")

    actual_hashes = {
        package["history_filename"]: sha256_file(history_path),
        package["coverage_filename"]: sha256_file(coverage_path),
        package["manifest_filename"]: sha256_file(manifest_path),
    }
    expected_hashes = {
        package["history_filename"]: package["history_sha256"],
        package["coverage_filename"]: package["coverage_sha256"],
        package["manifest_filename"]: package["manifest_sha256"],
    }
    if actual_hashes != expected_hashes:
        raise RuntimeError("Validation package artifact SHA-256 mismatch.")

    required_fields = set(package["required_record_fields"])
    expected_symbols = list(package["symbols"])
    expected_symbol_set = set(expected_symbols)
    expected_count = int(package["common_observation_count"])
    expected_rows = int(package["expected_history_row_count"])
    required_provider = package["required_source_provider"]

    counts: dict[str, int] = defaultdict(int)
    dates_by_symbol: dict[str, list[str]] = defaultdict(list)
    seen_keys: set[tuple[str, str]] = set()
    history_rows = 0
    null_required_price_count = 0
    invalid_ohlc_count = 0

    with history_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = json.loads(line)
            missing = required_fields.difference(record)
            if missing:
                raise RuntimeError(f"Missing required record fields on line {line_number}: {sorted(missing)}")

            ticker = str(record["ticker"])
            date = str(record["observation_date"])
            if ticker not in expected_symbol_set:
                raise RuntimeError(f"Unexpected ticker in validation package: {ticker}")
            if record["asset_id"] != f"metals:vehicle:{ticker}":
                raise RuntimeError(f"Asset ID mismatch for {ticker} on {date}.")
            if record["package_id"] != package["package_id"]:
                raise RuntimeError(f"Package ID mismatch for {ticker} on {date}.")
            if record["source_provider"] != required_provider:
                raise RuntimeError(f"Source provider mismatch for {ticker} on {date}.")

            key = (ticker, date)
            if key in seen_keys:
                raise RuntimeError(f"Duplicate ticker/date row detected: {ticker} {date}")
            seen_keys.add(key)

            price_fields = ("open_usd", "high_usd", "low_usd", "close_usd", "adjusted_close_usd")
            if any(record[field] is None for field in price_fields):
                null_required_price_count += 1
                continue

            open_price = float(record["open_usd"])
            high_price = float(record["high_usd"])
            low_price = float(record["low_usd"])
            close_price = float(record["close_usd"])
            adjusted_close = float(record["adjusted_close_usd"])
            if min(open_price, high_price, low_price, close_price, adjusted_close) <= 0:
                raise RuntimeError(f"Nonpositive price encountered for {ticker} on {date}.")
            if high_price < max(open_price, close_price, low_price) or low_price > min(open_price, close_price, high_price):
                invalid_ohlc_count += 1

            counts[ticker] += 1
            dates_by_symbol[ticker].append(date)
            history_rows += 1

    if null_required_price_count != 0:
        raise RuntimeError("Required price nulls detected in validation package.")
    if invalid_ohlc_count != 0:
        raise RuntimeError("OHLC consistency violations detected in validation package.")
    if history_rows != expected_rows:
        raise RuntimeError(f"History row count mismatch: expected {expected_rows}, observed {history_rows}.")
    if set(counts) != expected_symbol_set:
        raise RuntimeError("Validation package symbol set did not reconcile.")
    for ticker in expected_symbols:
        if counts[ticker] != expected_count:
            raise RuntimeError(f"Unexpected row count for {ticker}: {counts[ticker]}")
        dates_by_symbol[ticker].sort()
        if dates_by_symbol[ticker][0] != package["common_start_date"]:
            raise RuntimeError(f"Unexpected minimum date for {ticker}.")
        if dates_by_symbol[ticker][-1] != package["common_end_date"]:
            raise RuntimeError(f"Unexpected maximum date for {ticker}.")

    canonical_dates = dates_by_symbol[expected_symbols[0]]
    for ticker in expected_symbols[1:]:
        if dates_by_symbol[ticker] != canonical_dates:
            raise RuntimeError(f"Common calendar mismatch for {ticker}.")

    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if coverage["package_id"] != package["package_id"]:
        raise RuntimeError("Coverage package ID mismatch.")
    if int(coverage["common_observation_count"]) != expected_count:
        raise RuntimeError("Coverage common observation count mismatch.")
    if int(coverage["vehicle_count"]) != int(package["vehicle_count"]):
        raise RuntimeError("Coverage vehicle count mismatch.")
    if int(coverage["total_history_row_count"]) != expected_rows:
        raise RuntimeError("Coverage total history row count mismatch.")

    coverage_rows = list(coverage["coverage"])
    if len(coverage_rows) != int(package["vehicle_count"]):
        raise RuntimeError("Coverage row count mismatch.")
    for row in coverage_rows:
        ticker = row["ticker"]
        if ticker not in expected_symbol_set:
            raise RuntimeError(f"Unexpected coverage ticker: {ticker}")
        if int(row["observation_count"]) != expected_count:
            raise RuntimeError(f"Coverage observation count mismatch for {ticker}.")
        if row["min_date"] != package["common_start_date"] or row["max_date"] != package["common_end_date"]:
            raise RuntimeError(f"Coverage boundary mismatch for {ticker}.")
        expected_role = "REFERENCE_CONTROL" if ticker == "BIL" else "TACTICAL_OPPORTUNITY"
        if row["role"] != expected_role:
            raise RuntimeError(f"Coverage role mismatch for {ticker}.")

    if manifest["package_id"] != package["package_id"]:
        raise RuntimeError("Manifest package ID mismatch.")
    if manifest["collection_id"] != contract["source_collection"]:
        raise RuntimeError("Manifest collection lineage mismatch.")
    if manifest["source_collection_design"] != contract["source_collection_design"]:
        raise RuntimeError("Manifest collection-design lineage mismatch.")
    if manifest["source_candidate_rule_design"] != contract["source_candidate_rule_design"]:
        raise RuntimeError("Manifest candidate-rule lineage mismatch.")
    if manifest["source_provider"] != required_provider:
        raise RuntimeError("Manifest source provider mismatch.")
    if manifest["symbols"] != expected_symbols:
        raise RuntimeError("Manifest symbol order or set mismatch.")
    if int(manifest["common_observation_count"]) != expected_count or int(manifest["history_row_count"]) != expected_rows:
        raise RuntimeError("Manifest counts did not reconcile.")
    if manifest["common_start_date"] != package["common_start_date"] or manifest["common_end_date"] != package["common_end_date"]:
        raise RuntimeError("Manifest date boundary mismatch.")
    if manifest["artifact_sha256"].get(package["history_filename"]) != package["history_sha256"]:
        raise RuntimeError("Manifest history hash binding mismatch.")
    if manifest["artifact_sha256"].get(package["coverage_filename"]) != package["coverage_sha256"]:
        raise RuntimeError("Manifest coverage hash binding mismatch.")

    if manifest["outcome_blind"] is not True:
        raise RuntimeError("Outcome-blind manifest flag was not preserved.")
    for field in (
        "candidate_postures_calculated",
        "forward_returns_calculated",
        "maximum_adverse_or_favorable_excursion_calculated",
        "policy_pass_fail_checks_calculated",
        "new_validation_outcome_inspection_executed",
    ):
        if manifest[field] is not False:
            raise RuntimeError(f"Outcome-blind manifest control changed: {field}")

    result = {
        "status": "PASS",
        "read_only": True,
        "review_id": contract["review_id"],
        "source_collection": contract["source_collection"],
        "source_collection_design": contract["source_collection_design"],
        "source_candidate_rule_design": contract["source_candidate_rule_design"],
        "package_id": package["package_id"],
        "source_provider": required_provider,
        "common_start_date": package["common_start_date"],
        "common_end_date": package["common_end_date"],
        "common_observation_count": expected_count,
        "vehicle_count": int(package["vehicle_count"]),
        "opportunity_vehicle_count": int(package["opportunity_vehicle_count"]),
        "reference_control_count": 1,
        "history_row_count": history_rows,
        "history_sha256": actual_hashes[package["history_filename"]],
        "coverage_sha256": actual_hashes[package["coverage_filename"]],
        "manifest_sha256": actual_hashes[package["manifest_filename"]],
        "exact_common_calendar_verified": True,
        "duplicate_ticker_date_count": 0,
        "required_price_null_count": 0,
        "ohlc_consistency_violation_count": 0,
        "outcome_blind_controls_verified": True,
        "network_query_executed": False,
        "candidate_postures_calculated": False,
        "forward_returns_calculated": False,
        "maximum_adverse_or_favorable_excursion_calculated": False,
        "historical_candidate_evaluation_authorized": controls["historical_candidate_evaluation_authorized"],
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": controls["cross_domain_rank_authorized"],
        "allocation_policy_authorized": controls["allocation_policy_authorized"],
        "automatic_execution_authorized": controls["automatic_execution_authorized"],
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
