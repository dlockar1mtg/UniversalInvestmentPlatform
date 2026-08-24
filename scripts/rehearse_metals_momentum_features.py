from __future__ import annotations

import json
import math
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "momentum_feature_contract.json"
BENCHMARKS = {
    "BIL": "^IRX", "COPX": "HG=F", "CPER": "HG=F", "GLD": "GC=F",
    "IAU": "GC=F", "PPLT": "PL=F", "SGOL": "GC=F", "SIVR": "SI=F",
    "SLV": "SI=F", "URA": "URA", "URNM": "URA",
}


def pct_return(values: list[float], window: int) -> float:
    if len(values) <= window:
        raise RuntimeError(f"insufficient observations for {window}-observation return")
    return (values[-1] / values[-1 - window] - 1.0) * 100.0


def distance_ma(values: list[float], window: int) -> float:
    if len(values) < window:
        raise RuntimeError(f"insufficient observations for {window}-observation moving average")
    avg = sum(values[-window:]) / window
    return (values[-1] / avg - 1.0) * 100.0


def drawdowns(values: list[float]) -> tuple[float, float]:
    peak = values[0]
    max_dd = 0.0
    current_dd = 0.0
    for value in values:
        peak = max(peak, value)
        dd = (value / peak - 1.0) * 100.0
        max_dd = min(max_dd, dd)
        current_dd = dd
    return current_dd, max_dd


def realized_vol(values: list[float], annualization: int) -> float:
    rets = [(values[i] / values[i - 1] - 1.0) for i in range(1, len(values))]
    if len(rets) < 2:
        raise RuntimeError("insufficient observations for realized volatility")
    return statistics.stdev(rets) * math.sqrt(annualization) * 100.0


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-MOMENTUM-1":
        raise RuntimeError("unexpected Metals momentum contract")
    controls = contract.get("controls") or {}
    if controls.get("momentum_feature_calculation_authorized") is not True:
        raise RuntimeError("momentum feature calculation is not authorized")
    if any(controls.get(key) is not False for key in (
        "production_database_write_authorized", "forecast_refresh_authorized",
        "model_retraining_authorized", "momentum_interpretation_policy_authorized",
        "tactical_posture_authorized", "cross_domain_rank_authorized",
        "allocation_policy_authorized", "automatic_execution_authorized",
    )):
        raise RuntimeError("momentum controls changed unexpectedly")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    import psycopg
    connection = psycopg.connect(dsn)
    try:
        connection.execute("BEGIN READ ONLY")
        vehicle_rows = connection.execute(
            """SELECT ticker, observation_date, COALESCE(adjusted_close, close) AS px
               FROM metals_vehicle_observations
               WHERE source=%s AND run_id=%s
               ORDER BY ticker, observation_date""",
            (contract["source"], contract["run_id"]),
        ).fetchall()
        benchmark_rows = connection.execute(
            """SELECT benchmark_symbol, observation_date, close
               FROM metals_market_benchmark_observations
               WHERE source=%s AND run_id=%s
               ORDER BY benchmark_symbol, observation_date""",
            (contract["source"], contract["run_id"]),
        ).fetchall()
        connection.rollback()
    finally:
        connection.close()

    vehicle: dict[str, list[float]] = {}
    for ticker, _date, px in vehicle_rows:
        vehicle.setdefault(str(ticker), []).append(float(px))
    benchmark: dict[str, list[float]] = {}
    for symbol, _date, px in benchmark_rows:
        benchmark.setdefault(str(symbol), []).append(float(px))

    if set(vehicle) != set(BENCHMARKS):
        raise RuntimeError("vehicle history does not match governed ticker set")
    if set(benchmark) != set(BENCHMARKS.values()):
        raise RuntimeError("benchmark history does not match governed benchmark set")

    minimum = int(contract["minimum_vehicle_observations"])
    windows = {k: int(v) for k, v in contract["return_windows"].items()}
    annualization = int(contract["annualization_factor"])
    rows: list[dict[str, object]] = []
    for ticker in sorted(vehicle):
        values = vehicle[ticker]
        if len(values) < minimum:
            raise RuntimeError(f"insufficient governed history for {ticker}")
        bench_symbol = BENCHMARKS[ticker]
        bench_values = benchmark[bench_symbol]
        if len(bench_values) < minimum:
            raise RuntimeError(f"insufficient governed benchmark history for {bench_symbol}")

        trailing_252 = values[-252:]
        current_dd, max_dd = drawdowns(trailing_252)
        low_52 = min(trailing_252)
        high_52 = max(trailing_252)
        range_position = 50.0 if high_52 == low_52 else ((values[-1] - low_52) / (high_52 - low_52)) * 100.0
        r1 = pct_return(values, windows["1m"])
        r3 = pct_return(values, windows["3m"])
        r6 = pct_return(values, windows["6m"])
        r12 = pct_return(values, windows["12m"])
        bench_r3 = pct_return(bench_values, windows["3m"])
        rows.append({
            "ticker": ticker,
            "benchmark_symbol": bench_symbol,
            "observation_count": len(values),
            "return_1m_pct": round(r1, 6),
            "return_3m_pct": round(r3, 6),
            "return_6m_pct": round(r6, 6),
            "return_12m_pct": round(r12, 6),
            "distance_ma20_pct": round(distance_ma(values, 20), 6),
            "distance_ma50_pct": round(distance_ma(values, 50), 6),
            "distance_ma200_pct": round(distance_ma(values, 200), 6),
            "position_52w_range_pct": round(range_position, 6),
            "current_drawdown_pct": round(current_dd, 6),
            "max_drawdown_52w_pct": round(max_dd, 6),
            "realized_volatility_3m_pct": round(realized_vol(values[-64:], annualization), 6),
            "benchmark_relative_return_3m_pct": round(r3 - bench_r3, 6),
            "momentum_acceleration_pct": round(r1 - r3, 6),
        })

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": "METALS-MOMENTUM-1",
        "source_authority": "METALS-MARKET-HISTORY-1",
        "feature_row_count": len(rows),
        "features": rows,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "momentum_feature_calculation_authorized": True,
        "momentum_interpretation_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": "REVIEW_METALS_MOMENTUM_FEATURE_BEHAVIOR",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
