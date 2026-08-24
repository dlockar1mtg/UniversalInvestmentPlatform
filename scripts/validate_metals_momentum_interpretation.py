from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "momentum_interpretation_validation_contract.json"
BENCHMARKS = {
    "BIL": "^IRX", "COPX": "HG=F", "CPER": "HG=F", "GLD": "GC=F",
    "IAU": "GC=F", "PPLT": "PL=F", "SGOL": "GC=F", "SIVR": "SI=F",
    "SLV": "SI=F", "URA": "URA", "URNM": "URA",
}
GOLD_FAMILY = ("GLD", "IAU", "SGOL")
SILVER_FAMILY = ("SIVR", "SLV")


def pct_return(values: list[float], window: int) -> float:
    return (values[-1] / values[-1 - window] - 1.0) * 100.0


def distance_ma(values: list[float], window: int) -> float:
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


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "METALS-MOMENTUM-VALIDATION-1":
        raise RuntimeError("unexpected momentum interpretation validation contract")
    controls = contract.get("controls") or {}
    if controls.get("candidate_state_evaluation_authorized") is not True:
        raise RuntimeError("candidate-state evaluation is not authorized")
    prohibited = (
        "production_database_write_authorized", "forecast_refresh_authorized",
        "model_retraining_authorized", "momentum_interpretation_policy_authorized",
        "tactical_posture_authorized", "cross_domain_rank_authorized",
        "allocation_policy_authorized", "automatic_execution_authorized",
    )
    if any(controls.get(key) is not False for key in prohibited):
        raise RuntimeError("validation controls changed unexpectedly")

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
    for ticker, _date, px in rows:
        series[str(ticker)].append(float(px))
    if set(series) != set(BENCHMARKS):
        raise RuntimeError("vehicle history does not match governed ticker set")

    minimum = int(contract["minimum_history_observations"])
    step = int(contract["evaluation_step_observations"])
    allowed = set(contract["candidate_states"])
    state_counts: dict[str, Counter[str]] = {}
    transition_counts: Counter[str] = Counter()
    evaluation_counts: dict[str, int] = {}
    state_sequences: dict[str, list[str]] = {}

    for ticker in sorted(series):
        values = series[ticker]
        if len(values) < minimum:
            raise RuntimeError(f"insufficient governed history for {ticker}")
        states: list[str] = []
        for end in range(minimum, len(values) + 1, step):
            state = candidate_state(values[:end])
            if state not in allowed:
                raise RuntimeError(f"unexpected candidate state for {ticker}: {state}")
            states.append(state)
        if not states:
            raise RuntimeError(f"no candidate states evaluated for {ticker}")
        state_sequences[ticker] = states
        state_counts[ticker] = Counter(states)
        evaluation_counts[ticker] = len(states)
        for previous, current in zip(states, states[1:]):
            transition_counts[f"{previous}->{current}"] += 1

    def family_disagreement(tickers: tuple[str, ...]) -> dict[str, object]:
        lengths = {len(state_sequences[ticker]) for ticker in tickers}
        if len(lengths) != 1:
            raise RuntimeError(f"family evaluation lengths differ: {tickers}")
        total = next(iter(lengths))
        disagreements = 0
        for index in range(total):
            states = {state_sequences[ticker][index] for ticker in tickers}
            if len(states) > 1:
                disagreements += 1
        return {
            "tickers": list(tickers),
            "evaluation_points": total,
            "disagreement_points": disagreements,
            "disagreement_rate_pct": round((disagreements / total) * 100.0, 6),
        }

    aggregate = Counter()
    for counts in state_counts.values():
        aggregate.update(counts)

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": "METALS-MOMENTUM-VALIDATION-1",
        "source_authority": "METALS-MOMENTUM-1",
        "evaluation_step_observations": step,
        "vehicle_evaluation_counts": evaluation_counts,
        "candidate_state_counts_by_vehicle": {ticker: dict(sorted(counts.items())) for ticker, counts in state_counts.items()},
        "aggregate_candidate_state_counts": dict(sorted(aggregate.items())),
        "transition_counts": dict(sorted(transition_counts.items())),
        "family_consistency": {
            "gold_physical": family_disagreement(GOLD_FAMILY),
            "silver_physical": family_disagreement(SILVER_FAMILY),
        },
        "candidate_state_evaluation_authorized": True,
        "momentum_interpretation_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "next_decision": "REVIEW_METALS_MOMENTUM_INTERPRETATION_VALIDATION",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
