from __future__ import annotations

import json
import math
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "momentum_behavior_review_contract.json"
FEATURE_CONTRACT_PATH = ROOT / "config" / "metals" / "momentum_feature_contract.json"
BENCHMARKS = {
    "BIL": "^IRX", "COPX": "HG=F", "CPER": "HG=F", "GLD": "GC=F",
    "IAU": "GC=F", "PPLT": "PL=F", "SGOL": "GC=F", "SIVR": "SI=F",
    "SLV": "SI=F", "URA": "URA", "URNM": "URA",
}


def pct_return(values: list[float], window: int) -> float:
    return (values[-1] / values[-1 - window] - 1.0) * 100.0


def distance_ma(values: list[float], window: int) -> float:
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
    return statistics.stdev(rets) * math.sqrt(annualization) * 100.0


def _features(vehicle: dict[str, list[float]], benchmark: dict[str, list[float]], feature_contract: dict[str, object]) -> list[dict[str, float | int | str]]:
    windows = {k: int(v) for k, v in feature_contract["return_windows"].items()}
    annualization = int(feature_contract["annualization_factor"])
    rows: list[dict[str, float | int | str]] = []
    for ticker in sorted(vehicle):
        values = vehicle[ticker]
        bench_values = benchmark[BENCHMARKS[ticker]]
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
            "return_1m_pct": r1,
            "return_3m_pct": r3,
            "return_6m_pct": r6,
            "return_12m_pct": r12,
            "distance_ma20_pct": distance_ma(values, 20),
            "distance_ma50_pct": distance_ma(values, 50),
            "distance_ma200_pct": distance_ma(values, 200),
            "position_52w_range_pct": range_position,
            "current_drawdown_pct": current_dd,
            "max_drawdown_52w_pct": max_dd,
            "realized_volatility_3m_pct": realized_vol(values[-64:], annualization),
            "benchmark_relative_return_3m_pct": r3 - bench_r3,
            "momentum_acceleration_pct": r1 - r3,
        })
    return rows


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    feature_contract = json.loads(FEATURE_CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-MOMENTUM-REVIEW-1":
        raise RuntimeError("unexpected momentum behavior review contract")
    controls = contract.get("controls") or {}
    if controls.get("momentum_feature_calculation_authorized") is not True:
        raise RuntimeError("momentum feature calculation is not authorized")
    for key in (
        "production_database_write_authorized", "forecast_refresh_authorized",
        "model_retraining_authorized", "momentum_interpretation_policy_authorized",
        "tactical_posture_authorized", "cross_domain_rank_authorized",
        "allocation_policy_authorized", "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"unexpected control authorization: {key}")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    import psycopg
    connection = psycopg.connect(dsn)
    try:
        connection.execute("BEGIN READ ONLY")
        source = feature_contract["source"]
        run_id = feature_contract["run_id"]
        vehicle_rows = connection.execute(
            """SELECT ticker, observation_date, COALESCE(adjusted_close, close) AS px
               FROM metals_vehicle_observations WHERE source=%s AND run_id=%s
               ORDER BY ticker, observation_date""",
            (source, run_id),
        ).fetchall()
        benchmark_rows = connection.execute(
            """SELECT benchmark_symbol, observation_date, close
               FROM metals_market_benchmark_observations WHERE source=%s AND run_id=%s
               ORDER BY benchmark_symbol, observation_date""",
            (source, run_id),
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

    rows = _features(vehicle, benchmark, feature_contract)
    if len(rows) != int(contract["required_vehicle_count"]):
        raise RuntimeError("unexpected momentum feature row count")

    fields = list(contract["review_fields"])
    cross_section = {}
    for field in fields:
        values = [float(row[field]) for row in rows]
        cross_section[field] = {
            "min": round(min(values), 6),
            "max": round(max(values), 6),
            "median": round(statistics.median(values), 6),
            "range": round(max(values) - min(values), 6),
        }

    family_consistency = {}
    rows_by_ticker = {str(row["ticker"]): row for row in rows}
    for family, tickers in contract["family_consistency_groups"].items():
        metrics = {}
        for field in fields:
            values = [float(rows_by_ticker[ticker][field]) for ticker in tickers]
            metrics[field] = round(max(values) - min(values), 6)
        family_consistency[family] = {
            "tickers": tickers,
            "max_spread_by_feature": metrics,
        }

    sign_patterns = {}
    for row in rows:
        ticker = str(row["ticker"])
        sign_patterns[ticker] = {
            "return_1m_positive": float(row["return_1m_pct"]) > 0,
            "return_3m_positive": float(row["return_3m_pct"]) > 0,
            "return_6m_positive": float(row["return_6m_pct"]) > 0,
            "return_12m_positive": float(row["return_12m_pct"]) > 0,
            "above_ma20": float(row["distance_ma20_pct"]) > 0,
            "above_ma50": float(row["distance_ma50_pct"]) > 0,
            "above_ma200": float(row["distance_ma200_pct"]) > 0,
            "benchmark_relative_3m_positive": float(row["benchmark_relative_return_3m_pct"]) > 0,
            "momentum_acceleration_positive": float(row["momentum_acceleration_pct"]) > 0,
        }

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": "METALS-MOMENTUM-REVIEW-1",
        "source_authority": "METALS-MOMENTUM-1",
        "feature_row_count": len(rows),
        "cross_section": cross_section,
        "family_consistency": family_consistency,
        "sign_patterns": sign_patterns,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "momentum_interpretation_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": "DESIGN_METALS_MOMENTUM_INTERPRETATION_VALIDATION",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
