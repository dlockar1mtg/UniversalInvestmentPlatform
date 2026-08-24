from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_historical_expansion_collection.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scalar(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return float(value)


def normalize_frame(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if frame.empty:
        raise RuntimeError(f"No historical rows returned for {symbol}.")
    if isinstance(frame.columns, pd.MultiIndex):
        frame = frame.copy()
        frame.columns = [col[0] if isinstance(col, tuple) else col for col in frame.columns]
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise RuntimeError(f"Missing required source fields for {symbol}: {missing}")
    normalized = frame.copy()
    normalized.index = pd.to_datetime(normalized.index).tz_localize(None).normalize()
    normalized = normalized[~normalized.index.duplicated(keep="last")].sort_index()
    if "Adj Close" not in normalized.columns:
        normalized["Adj Close"] = normalized["Close"]
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    boundary = auth["collection_boundary"]
    source = auth["source_contract"]
    artifacts = auth["artifact_contract"]
    controls = auth["controls"]

    assert controls["historical_expansion_collection_authorized"] is True
    assert controls["historical_candidate_evaluation_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["production_database_write_authorized"] is False

    symbols = list(source["symbols"])
    start_date = boundary["common_start_date"]
    end_date = boundary["common_end_date"]
    expected_count = int(boundary["expected_common_observation_count"])
    exclusive_end = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    frames: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        raw = yf.download(
            symbol,
            start=start_date,
            end=exclusive_end,
            interval=source["daily_interval"],
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=False,
        )
        frames[symbol] = normalize_frame(raw, symbol)

    common_dates = None
    for symbol in symbols:
        dates = set(frames[symbol].index)
        common_dates = dates if common_dates is None else common_dates.intersection(dates)
    ordered_dates = sorted(common_dates or [])

    if len(ordered_dates) != expected_count:
        raise RuntimeError(
            f"Common-calendar observation count mismatch: expected {expected_count}, observed {len(ordered_dates)}."
        )
    if ordered_dates[0].strftime("%Y-%m-%d") != start_date:
        raise RuntimeError("Common-calendar start date changed.")
    if ordered_dates[-1].strftime("%Y-%m-%d") != end_date:
        raise RuntimeError("Common-calendar end date changed.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    history_path = output_dir / artifacts["history_filename"]
    coverage_path = output_dir / artifacts["coverage_filename"]
    manifest_path = output_dir / artifacts["manifest_filename"]

    history_count = 0
    with history_path.open("w", encoding="utf-8", newline="\n") as handle:
        for symbol in symbols:
            frame = frames[symbol]
            for date in ordered_dates:
                row = frame.loc[date]
                record = {
                    "asset_id": f"metals:vehicle:{symbol}",
                    "ticker": symbol,
                    "observation_date": date.strftime("%Y-%m-%d"),
                    "open_usd": scalar(row["Open"]),
                    "high_usd": scalar(row["High"]),
                    "low_usd": scalar(row["Low"]),
                    "close_usd": scalar(row["Close"]),
                    "adjusted_close_usd": scalar(row["Adj Close"]),
                    "volume": scalar(row["Volume"]),
                    "source_provider": source["provider"],
                    "package_id": auth["package_id"],
                }
                if any(record[field] is None for field in ("open_usd", "high_usd", "low_usd", "close_usd", "adjusted_close_usd")):
                    raise RuntimeError(f"Missing required price field for {symbol} on {record['observation_date']}.")
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
                history_count += 1

    expected_history_count = expected_count * len(symbols)
    if history_count != expected_history_count:
        raise RuntimeError("Persisted history row count did not reconcile.")

    coverage = {
        "package_id": auth["package_id"],
        "common_start_date": start_date,
        "common_end_date": end_date,
        "common_observation_count": expected_count,
        "vehicle_count": len(symbols),
        "total_history_row_count": history_count,
        "coverage": [
            {
                "asset_id": f"metals:vehicle:{symbol}",
                "ticker": symbol,
                "observation_count": expected_count,
                "min_date": start_date,
                "max_date": end_date,
                "role": "REFERENCE_CONTROL" if symbol == "BIL" else "TACTICAL_OPPORTUNITY",
            }
            for symbol in symbols
        ],
    }
    coverage_path.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "package_id": auth["package_id"],
        "collection_id": auth["collection_id"],
        "source_collection_design": auth["source_collection_design"],
        "source_candidate_rule_design": auth["source_candidate_rule_design"],
        "source_provider": source["provider"],
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "common_start_date": start_date,
        "common_end_date": end_date,
        "common_observation_count": expected_count,
        "symbols": symbols,
        "history_row_count": history_count,
        "artifact_sha256": {
            artifacts["history_filename"]: sha256_file(history_path),
            artifacts["coverage_filename"]: sha256_file(coverage_path),
        },
        "outcome_blind": True,
        "candidate_postures_calculated": False,
        "forward_returns_calculated": False,
        "maximum_adverse_or_favorable_excursion_calculated": False,
        "policy_pass_fail_checks_calculated": False,
        "new_validation_outcome_inspection_executed": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = {
        "status": "PASS",
        "collection_id": auth["collection_id"],
        "package_id": auth["package_id"],
        "source_provider": source["provider"],
        "common_start_date": start_date,
        "common_end_date": end_date,
        "common_observation_count": expected_count,
        "vehicle_count": len(symbols),
        "opportunity_vehicle_count": len(symbols) - 1,
        "reference_control_count": 1,
        "history_row_count": history_count,
        "history_sha256": sha256_file(history_path),
        "coverage_sha256": sha256_file(coverage_path),
        "manifest_sha256": sha256_file(manifest_path),
        "historical_expansion_collection_executed": True,
        "historical_expansion_persisted": True,
        "candidate_postures_calculated": False,
        "forward_returns_calculated": False,
        "maximum_adverse_or_favorable_excursion_calculated": False,
        "policy_pass_fail_checks_calculated": False,
        "new_validation_outcome_inspection_executed": False,
        "historical_candidate_evaluation_authorized": False,
        "tactical_posture_authorized": False,
        "presentation_activation_executed": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": auth["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
