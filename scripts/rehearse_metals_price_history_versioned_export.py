from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_PATH = ROOT / "config" / "presentation" / "metals_price_history_versioned_export_rehearsal.json"
TICKERS = ("BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str))
            handle.write("\n")


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-PRICE-HISTORY-VERSIONED-EXPORT-REHEARSAL-1":
        raise RuntimeError("unexpected versioned export rehearsal contract")
    controls = contract.get("controls") or {}
    if controls.get("native_source_read_authorized") is not True:
        raise RuntimeError("native source read is not authorized")
    if controls.get("versioned_export_execution_authorized") is not True:
        raise RuntimeError("versioned export execution is not authorized")
    for key in (
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
            raise RuntimeError(f"prohibited control changed unexpectedly: {key}")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    output_dir = Path(parse_args().output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise RuntimeError(f"output directory must be empty: {output_dir}")

    import psycopg

    connection = psycopg.connect(dsn)
    try:
        connection.execute("BEGIN READ ONLY")
        rows = connection.execute(
            """SELECT ticker, observation_date, close, adjusted_close, volume, source, run_id
               FROM metals_vehicle_observations
               WHERE source=%s AND run_id=%s
               ORDER BY ticker, observation_date""",
            (contract["source_system"], contract["source_run_id"]),
        ).fetchall()
        connection.rollback()
    finally:
        connection.close()

    expected_history = int(contract["expected_history_point_count"])
    if len(rows) != expected_history:
        raise RuntimeError(f"unexpected governed history row count: {len(rows)}")

    observed_tickers = sorted({str(row[0]) for row in rows})
    if observed_tickers != sorted(TICKERS):
        raise RuntimeError(f"unexpected governed ticker set: {observed_tickers}")

    history: list[dict[str, object]] = []
    latest_by_ticker: dict[str, dict[str, object]] = {}
    seen_keys: set[tuple[str, str]] = set()

    for ticker_raw, observation_date, close, adjusted_close, volume, source, run_id in rows:
        ticker = str(ticker_raw)
        date_text = str(observation_date)
        key = (ticker, date_text)
        if key in seen_keys:
            raise RuntimeError(f"duplicate governed history key: {ticker} {date_text}")
        seen_keys.add(key)
        if close is None or float(close) <= 0:
            raise RuntimeError(f"invalid close for {ticker} {date_text}")
        if adjusted_close is not None and float(adjusted_close) <= 0:
            raise RuntimeError(f"invalid adjusted close for {ticker} {date_text}")
        if volume is not None and float(volume) < 0:
            raise RuntimeError(f"invalid volume for {ticker} {date_text}")
        effective = float(adjusted_close if adjusted_close is not None else close)
        history_row = {
            "asset_id": f"metals:vehicle:{ticker}",
            "ticker": ticker,
            "observation_date": date_text,
            "close_usd": float(close),
            "adjusted_close_usd": None if adjusted_close is None else float(adjusted_close),
            "volume": None if volume is None else float(volume),
            "source_authority": contract["source_authority"],
            "source_system": str(source),
            "source_run_id": str(run_id),
        }
        history.append(history_row)
        latest_by_ticker[ticker] = {
            "asset_id": f"metals:vehicle:{ticker}",
            "ticker": ticker,
            "observation_date": date_text,
            "current_price_usd": effective,
            "source_authority": contract["source_authority"],
            "source_system": str(source),
            "source_run_id": str(run_id),
        }

    current = [latest_by_ticker[ticker] for ticker in sorted(TICKERS)]
    if len(current) != int(contract["expected_vehicle_count"]):
        raise RuntimeError("current-price record count does not reconcile")

    current_path = output_dir / str(contract["current_price_filename"])
    history_path = output_dir / str(contract["price_history_filename"])
    manifest_path = output_dir / str(contract["manifest_filename"])
    write_jsonl(current_path, current)
    write_jsonl(history_path, history)

    files = {
        current_path.name: {
            "sha256": sha256_file(current_path),
            "record_count": len(current),
            "record_type": contract["current_price_record_type"],
        },
        history_path.name: {
            "sha256": sha256_file(history_path),
            "record_count": len(history),
            "record_type": contract["price_history_record_type"],
        },
    }
    manifest = {
        "package_id": "metals-price-history-20260824",
        "contract_id": contract["contract_id"],
        "source_authority": contract["source_authority"],
        "source_system": contract["source_system"],
        "source_run_id": contract["source_run_id"],
        "vehicle_count": len(current),
        "history_point_count": len(history),
        "files": files,
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    manifest_sha = sha256_file(manifest_path)

    result = {
        "status": "PASS",
        "read_only_native_source": True,
        "contract_id": contract["contract_id"],
        "package_id": manifest["package_id"],
        "source_authority": contract["source_authority"],
        "source_run_id": contract["source_run_id"],
        "output_dir": str(output_dir),
        "current_price_record_count": len(current),
        "history_point_count": len(history),
        "vehicle_count": len(observed_tickers),
        "current_price_sha256": files[current_path.name]["sha256"],
        "price_history_sha256": files[history_path.name]["sha256"],
        "manifest_sha256": manifest_sha,
        "current_prices": current,
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
