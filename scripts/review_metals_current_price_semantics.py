from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "current_price_semantic_review.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL at {path.name}:{line_number}") from exc
    return rows


def close_enough(left, right, tolerance: float) -> bool:
    if left is None or right is None:
        return False
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    args = parser.parse_args()

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    source = contract["source_package"]
    semantic = contract["semantic_target"]
    controls = contract["controls"]

    assert controls["semantic_review_authorized"] is True
    assert controls["native_source_query_authorized"] is False
    assert controls["package_regeneration_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["production_database_write_authorized"] is False

    package_dir = Path(args.package_dir)
    current_path = package_dir / source["current_filename"]
    history_path = package_dir / source["history_filename"]
    manifest_path = package_dir / source["manifest_filename"]

    for path in (current_path, history_path, manifest_path):
        if not path.is_file():
            raise RuntimeError(f"Required package artifact missing: {path}")

    hashes = {
        "current": sha256_file(current_path),
        "history": sha256_file(history_path),
        "manifest": sha256_file(manifest_path),
    }
    if hashes["current"] != source["current_sha256"]:
        raise RuntimeError("Current-price artifact SHA-256 mismatch.")
    if hashes["history"] != source["history_sha256"]:
        raise RuntimeError("Price-history artifact SHA-256 mismatch.")
    if hashes["manifest"] != source["manifest_sha256"]:
        raise RuntimeError("Manifest SHA-256 mismatch.")

    current_rows = load_jsonl(current_path)
    history_rows = load_jsonl(history_path)
    expected_symbols = list(source["symbols"])

    if len(current_rows) != int(source["expected_vehicle_count"]):
        raise RuntimeError("Unexpected current-price row count.")

    current_by_ticker = {}
    for row in current_rows:
        ticker = row.get("ticker")
        if ticker in current_by_ticker:
            raise RuntimeError(f"Duplicate current-price ticker: {ticker}")
        current_by_ticker[ticker] = row
    if sorted(current_by_ticker) != sorted(expected_symbols):
        raise RuntimeError("Current-price symbol set mismatch.")

    latest_by_ticker = {}
    for row in history_rows:
        ticker = row.get("ticker")
        if ticker not in expected_symbols:
            continue
        date = row.get("observation_date")
        if ticker not in latest_by_ticker or date > latest_by_ticker[ticker].get("observation_date", ""):
            latest_by_ticker[ticker] = row
    if sorted(latest_by_ticker) != sorted(expected_symbols):
        raise RuntimeError("History does not contain all governed symbols.")

    tolerance = float(semantic["comparison_tolerance"])
    classifications = []
    certified = True
    for ticker in expected_symbols:
        current = current_by_ticker[ticker]
        latest = latest_by_ticker[ticker]
        published = current.get(semantic["published_field"])
        raw_close = latest.get(semantic["history_reference_field"])
        adjusted_close = latest.get(semantic["comparison_field"])
        raw_match = close_enough(published, raw_close, tolerance)
        adjusted_match = close_enough(published, adjusted_close, tolerance)
        if raw_match and adjusted_match:
            classification = "BOTH"
        elif raw_match:
            classification = "RAW_CLOSE"
        elif adjusted_match:
            classification = "ADJUSTED_CLOSE"
        else:
            classification = "NEITHER"
        if not raw_match:
            certified = False
        classifications.append({
            "ticker": ticker,
            "current_observation_date": current.get("observation_date"),
            "history_latest_observation_date": latest.get("observation_date"),
            "current_price_usd": published,
            "latest_close_usd": raw_close,
            "latest_adjusted_close_usd": adjusted_close,
            "matches_unadjusted_close": raw_match,
            "matches_adjusted_close": adjusted_match,
            "classification": classification,
        })

    next_decision = (
        contract["next_decision_if_certified"]
        if certified
        else contract["next_decision_if_not_certified"]
    )

    result = {
        "status": "PASS",
        "read_only": True,
        "review_id": contract["review_id"],
        "package_id": source["package_id"],
        "required_price_basis": semantic["required_basis"],
        "vehicle_count": len(expected_symbols),
        "current_price_semantics_certified": certified,
        "classification_counts": {
            name: sum(1 for row in classifications if row["classification"] == name)
            for name in semantic["classifications"]
        },
        "classifications": classifications,
        "current_sha256": hashes["current"],
        "history_sha256": hashes["history"],
        "manifest_sha256": hashes["manifest"],
        "native_source_query_executed": False,
        "package_regeneration_executed": False,
        "presentation_activation_executed": False,
        "production_database_write_executed": False,
        "historical_candidate_evaluation_authorized": controls["historical_candidate_evaluation_authorized"],
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": controls["cross_domain_rank_authorized"],
        "allocation_policy_authorized": controls["allocation_policy_authorized"],
        "automatic_execution_authorized": controls["automatic_execution_authorized"],
        "next_decision": next_decision,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
