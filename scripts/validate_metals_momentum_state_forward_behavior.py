from __future__ import annotations

import json
import math
import os
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "momentum_state_forward_validation_contract.json"
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


def candidate_state(values: list[float]) -> str:
    r1 = pct_return(values, 21)
    r3 = pct_return(values, 63)
    r6 = pct_return(values, 126)
    ma20 = distance_ma(values, 20)
    ma50 = distance_ma(values, 50)
    ma200 = distance_ma(values, 200)
    acceleration = r1 - r3

    if r1 > 0 and acceleration > 0 and ma20 > 0 and (r3 <= 0 or r6 <= 0) and ma200 <= 0:
        return "POTENTIALLY_REVERSING"
    if r3 > 0 and r6 > 0 and ma50 > 0 and ma200 > 0:
        if r1 > 0 and acceleration > 0:
            return "STRENGTHENING_UPWARD"
        return "ESTABLISHED_UPWARD"
    if r6 > 0 and (r1 <= 0 or ma20 <= 0):
        return "WEAKENING_UPWARD"
    if r3 < 0 and r6 < 0 and ma50 < 0 and ma200 < 0:
        if r1 < 0 and acceleration < 0:
            return "STRENGTHENING_DOWNWARD"
        return "ESTABLISHED_DOWNWARD"
    return "NEUTRAL_CONSOLIDATING"


def summarize(values: list[float]) -> dict[str, float | int]:
    if not values:
        raise RuntimeError("cannot summarize empty forward-return sample")
    positive = sum(1 for value in values if value > 0)
    return {
        "sample_count": len(values),
        "mean_pct": round(statistics.fmean(values), 6),
        "median_pct": round(statistics.median(values), 6),
        "positive_rate_pct": round((positive / len(values)) * 100.0, 6),
        "min_pct": round(min(values), 6),
        "max_pct": round(max(values), 6),
    }


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-MOMENTUM-FORWARD-VALIDATION-1":
        raise RuntimeError("unexpected Metals forward-validation contract")
    controls = contract.get("controls") or {}
    if controls.get("candidate_state_forward_validation_authorized") is not True:
        raise RuntimeError("candidate-state forward validation is not authorized")
    prohibited = (
        "momentum_interpretation_policy_authorized", "tactical_posture_authorized",
        "cross_domain_rank_authorized", "allocation_policy_authorized",
        "automatic_execution_authorized", "production_database_write_authorized",
        "forecast_refresh_authorized", "model_retraining_authorized",
    )
    if any(controls.get(key) is not False for key in prohibited):
        raise RuntimeError("forward-validation controls changed unexpectedly")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    import psycopg
    connection = psycopg.connect(dsn)
    try:
        connection.execute("BEGIN READ ONLY")
        rows = connection.execute(
            """SELECT ticker, observation_date, COALESCE(adjusted_close, close) AS px
               FROM metals_vehicle_observations
               WHERE source=%s AND run_id=%s
               ORDER BY ticker, observation_date""",
            (contract["source"], contract["run_id"]),
        ).fetchall()
        connection.rollback()
    finally:
        connection.close()

    series: dict[str, list[float]] = defaultdict(list)
    for ticker, _date, px in rows:
        series[str(ticker)].append(float(px))
    if set(series) != set(BENCHMARKS):
        raise RuntimeError("vehicle history does not match governed ticker set")

    minimum = int(contract["minimum_history_observations"])
    step = int(contract["evaluation_step_observations"])
    forward_windows = {key: int(value) for key, value in contract["forward_windows"].items()}
    max_forward = max(forward_windows.values())
    allowed = set(contract["candidate_states"])

    by_state: dict[str, dict[str, list[float]]] = {
        state: {window: [] for window in forward_windows} for state in sorted(allowed)
    }
    by_vehicle_state: dict[str, dict[str, int]] = {}
    total_evaluations = 0

    for ticker in sorted(series):
        values = series[ticker]
        if len(values) < minimum + max_forward:
            raise RuntimeError(f"insufficient governed history for forward validation: {ticker}")
        counts: dict[str, int] = defaultdict(int)
        for end in range(minimum, len(values) - max_forward + 1, step):
            historical = values[:end]
            state = candidate_state(historical)
            if state not in allowed:
                raise RuntimeError(f"unexpected candidate state for {ticker}: {state}")
            counts[state] += 1
            total_evaluations += 1
            current = values[end - 1]
            for window_name, window in forward_windows.items():
                future = values[end - 1 + window]
                outcome = (future / current - 1.0) * 100.0
                if not math.isfinite(outcome):
                    raise RuntimeError(f"non-finite forward outcome for {ticker} {state} {window_name}")
                by_state[state][window_name].append(outcome)
        by_vehicle_state[ticker] = dict(sorted(counts.items()))

    state_forward_summary: dict[str, dict[str, object]] = {}
    observed_states = []
    for state in sorted(allowed):
        samples = by_state[state]
        if any(samples[window] for window in forward_windows):
            observed_states.append(state)
            state_forward_summary[state] = {
                window: summarize(samples[window]) for window in sorted(forward_windows)
            }

    if len(observed_states) < 2:
        raise RuntimeError("forward validation collapsed to fewer than two observed states")

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": "METALS-MOMENTUM-FORWARD-VALIDATION-1",
        "source_authority": "METALS-MOMENTUM-VALIDATION-1",
        "market_history_authority": "METALS-MARKET-HISTORY-1",
        "evaluation_step_observations": step,
        "total_evaluations": total_evaluations,
        "observed_candidate_states": observed_states,
        "candidate_state_counts_by_vehicle": by_vehicle_state,
        "state_forward_summary": state_forward_summary,
        "candidate_state_forward_validation_authorized": True,
        "momentum_interpretation_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "next_decision": "REVIEW_METALS_MOMENTUM_STATE_FORWARD_VALIDATION",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
