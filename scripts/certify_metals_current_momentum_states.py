from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "momentum_interpretation_policy_contract.json"
TICKERS = ("BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM")


def pct_return(values: list[float], window: int) -> float:
    if len(values) <= window:
        raise RuntimeError(f"insufficient observations for {window}-observation return")
    return (values[-1] / values[-1 - window] - 1.0) * 100.0


def distance_ma(values: list[float], window: int) -> float:
    if len(values) < window:
        raise RuntimeError(f"insufficient observations for {window}-observation moving average")
    avg = sum(values[-window:]) / window
    return (values[-1] / avg - 1.0) * 100.0


def state_for(values: list[float]) -> tuple[str, dict[str, float]]:
    r1 = pct_return(values, 21)
    r3 = pct_return(values, 63)
    r6 = pct_return(values, 126)
    ma20 = distance_ma(values, 20)
    ma50 = distance_ma(values, 50)
    ma200 = distance_ma(values, 200)
    acceleration = r1 - r3

    if r1 > 0 and acceleration > 0 and ma20 > 0 and (r3 <= 0 or r6 <= 0) and ma200 <= 0:
        state = "POTENTIALLY_REVERSING"
    elif r3 > 0 and r6 > 0 and ma50 > 0 and ma200 > 0:
        state = "STRENGTHENING_UPWARD" if r1 > 0 and acceleration > 0 else "ESTABLISHED_UPWARD"
    elif r6 > 0 and (r1 <= 0 or ma20 <= 0):
        state = "WEAKENING_UPWARD"
    elif r3 < 0 and r6 < 0 and ma50 < 0 and ma200 < 0:
        state = "STRENGTHENING_DOWNWARD" if r1 < 0 and acceleration < 0 else "ESTABLISHED_DOWNWARD"
    else:
        state = "NEUTRAL_CONSOLIDATING"

    return state, {
        "return_1m_pct": round(r1, 6),
        "return_3m_pct": round(r3, 6),
        "return_6m_pct": round(r6, 6),
        "distance_ma20_pct": round(ma20, 6),
        "distance_ma50_pct": round(ma50, 6),
        "distance_ma200_pct": round(ma200, 6),
        "momentum_acceleration_pct": round(acceleration, 6),
    }


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-MOMENTUM-INTERPRETATION-1":
        raise RuntimeError("unexpected momentum interpretation contract")
    controls = contract.get("controls") or {}
    if controls.get("momentum_interpretation_policy_authorized") is not True:
        raise RuntimeError("momentum interpretation policy is not authorized")
    if controls.get("state_is_descriptive_not_predictive") is not True:
        raise RuntimeError("momentum state semantic scope is not locked as descriptive")
    for key in (
        "tactical_posture_authorized", "cross_domain_rank_authorized",
        "allocation_policy_authorized", "automatic_execution_authorized",
        "production_database_write_authorized", "forecast_refresh_authorized",
        "model_retraining_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited control changed unexpectedly: {key}")

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
            ("yfinance", "metals-market-history-backfill-20260824"),
        ).fetchall()
        connection.rollback()
    finally:
        connection.close()

    series: dict[str, list[float]] = defaultdict(list)
    dates: dict[str, str] = {}
    for ticker, observation_date, px in rows:
        ticker = str(ticker)
        series[ticker].append(float(px))
        dates[ticker] = str(observation_date)

    if set(series) != set(TICKERS):
        raise RuntimeError("current momentum-state ticker coverage does not reconcile")

    allowed = set(contract["states"])
    states = []
    for ticker in sorted(TICKERS):
        values = series[ticker]
        if len(values) < 500:
            raise RuntimeError(f"insufficient governed history for {ticker}")
        state, evidence = state_for(values)
        if state not in allowed:
            raise RuntimeError(f"state outside governed vocabulary for {ticker}: {state}")
        states.append({
            "ticker": ticker,
            "observation_date": dates[ticker],
            "market_state": state,
            "semantic_scope": contract["semantic_scope"],
            "evidence": evidence,
        })

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": contract["contract_id"],
        "semantic_scope": contract["semantic_scope"],
        "current_state_count": len(states),
        "current_states": states,
        "momentum_interpretation_policy_authorized": True,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
