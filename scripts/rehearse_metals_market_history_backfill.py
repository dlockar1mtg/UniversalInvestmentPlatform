from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_registry import load_metals_registry
from scripts.collect_metals_daily_market_input import BENCHMARKS


CONTRACT_PATH = ROOT / "config" / "metals" / "market_history_authority_contract.json"


def _load_contract() -> dict[str, object]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("contract_id") != "METALS-MARKET-HISTORY-1":
        raise RuntimeError("Unexpected Metals market-history authority contract.")
    controls = payload.get("controls") or {}
    if controls != {
        "production_database_write_authorized": False,
        "forecast_refresh_authorized": False,
        "model_retraining_authorized": False,
        "momentum_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "missing_history_may_be_synthesized": False,
    }:
        raise RuntimeError("Metals market-history controls changed unexpectedly.")
    return payload


def _history(symbol: str, *, period: str, interval: str):
    import yfinance as yf

    frame = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
    frame = frame.dropna(subset=["Close"])
    if frame.empty:
        raise RuntimeError(f"No market history returned for {symbol}.")
    return frame


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect a non-production three-year Metals market-history backfill rehearsal.")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    contract = _load_contract()
    period = str(contract["collection_period"])
    interval = str(contract["interval"])
    minimum_vehicle = int(contract["minimum_vehicle_rows_per_ticker"])
    minimum_benchmark = int(contract["minimum_benchmark_rows_per_symbol"])
    maximum_age = int(contract["maximum_latest_market_age_days"])

    registry = load_metals_registry()
    enabled = tuple(sorted((vehicle for vehicle in registry.vehicles if vehicle.enabled), key=lambda item: item.ticker))
    enabled_tickers = tuple(vehicle.ticker for vehicle in enabled)
    expected_tickers = tuple(sorted(BENCHMARKS))
    if enabled_tickers != expected_tickers:
        raise RuntimeError(f"Enabled vehicle registry does not match daily-market benchmark map: {enabled_tickers} vs {expected_tickers}")

    vehicle_rows: list[dict[str, object]] = []
    vehicle_coverage: list[dict[str, object]] = []
    for vehicle in enabled:
        frame = _history(vehicle.ticker, period=period, interval=interval)
        for timestamp, row in frame.iterrows():
            adjusted = row.get("Adj Close")
            volume = row.get("Volume")
            vehicle_rows.append({
                "ticker": vehicle.ticker,
                "observation_date": timestamp.date().isoformat(),
                "close": float(row["Close"]),
                "adjusted_close": "" if adjusted is None else float(adjusted),
                "volume": "" if volume is None else float(volume),
                "source": "yfinance",
            })
        min_date = frame.index[0].date()
        max_date = frame.index[-1].date()
        row_count = len(frame)
        latest_age = (args.as_of_date - max_date).days
        vehicle_coverage.append({
            "ticker": vehicle.ticker,
            "row_count": row_count,
            "min_observation_date": min_date.isoformat(),
            "max_observation_date": max_date.isoformat(),
            "latest_age_days": latest_age,
            "minimum_rows_pass": row_count >= minimum_vehicle,
            "freshness_pass": 0 <= latest_age <= maximum_age,
        })

    benchmark_symbols = tuple(sorted(set(BENCHMARKS.values())))
    benchmark_rows: list[dict[str, object]] = []
    benchmark_coverage: list[dict[str, object]] = []
    for symbol in benchmark_symbols:
        frame = _history(symbol, period=period, interval=interval)
        for timestamp, row in frame.iterrows():
            benchmark_rows.append({
                "benchmark_symbol": symbol,
                "observation_date": timestamp.date().isoformat(),
                "close": float(row["Close"]),
                "source": "yfinance",
            })
        min_date = frame.index[0].date()
        max_date = frame.index[-1].date()
        row_count = len(frame)
        latest_age = (args.as_of_date - max_date).days
        benchmark_coverage.append({
            "benchmark_symbol": symbol,
            "row_count": row_count,
            "min_observation_date": min_date.isoformat(),
            "max_observation_date": max_date.isoformat(),
            "latest_age_days": latest_age,
            "minimum_rows_pass": row_count >= minimum_benchmark,
            "freshness_pass": 0 <= latest_age <= maximum_age,
        })

    vehicle_pass = all(item["minimum_rows_pass"] and item["freshness_pass"] for item in vehicle_coverage)
    benchmark_pass = all(item["minimum_rows_pass"] and item["freshness_pass"] for item in benchmark_coverage)
    if not vehicle_pass or not benchmark_pass:
        raise RuntimeError(
            "Three-year market-history rehearsal did not satisfy the governed coverage contract. "
            f"vehicle_pass={vehicle_pass}; benchmark_pass={benchmark_pass}"
        )

    output_root = args.output_root.resolve()
    _write_csv(
        output_root / "vehicle_history.csv",
        vehicle_rows,
        ["ticker", "observation_date", "close", "adjusted_close", "volume", "source"],
    )
    _write_csv(
        output_root / "benchmark_market_history.csv",
        benchmark_rows,
        ["benchmark_symbol", "observation_date", "close", "source"],
    )

    summary = {
        "status": "PASS",
        "rehearsal_only": True,
        "contract_id": contract["contract_id"],
        "collection_period": period,
        "interval": interval,
        "as_of_date": args.as_of_date.isoformat(),
        "vehicle_row_count": len(vehicle_rows),
        "benchmark_row_count": len(benchmark_rows),
        "vehicle_coverage": vehicle_coverage,
        "benchmark_coverage": benchmark_coverage,
        "production_database_write_authorized": False,
        "forecast_refresh_authorized": False,
        "model_retraining_authorized": False,
        "momentum_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "missing_history_may_be_synthesized": False,
        "next_decision": "AUTHORIZE_METALS_MARKET_HISTORY_BACKFILL_INGESTION_REHEARSAL",
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
