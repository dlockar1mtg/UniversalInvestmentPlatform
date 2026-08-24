from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "momentum_state_publication_rehearsal_contract.json"
TICKERS = ("BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM")


def pct_return(values: list[float], window: int) -> float:
    return (values[-1] / values[-1 - window] - 1.0) * 100.0


def distance_ma(values: list[float], window: int) -> float:
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
    if contract.get("contract_id") != "METALS-MOMENTUM-PUBLICATION-REHEARSAL-1":
        raise RuntimeError("unexpected momentum publication rehearsal contract")
    controls = contract.get("controls") or {}
    if controls.get("publication_projection_rehearsal_authorized") is not True:
        raise RuntimeError("publication projection rehearsal is not authorized")
    prohibited = (
        "presentation_activation_authorized", "production_database_write_authorized",
        "forecast_refresh_authorized", "model_retraining_authorized",
        "tactical_posture_authorized", "cross_domain_rank_authorized",
        "allocation_policy_authorized", "automatic_execution_authorized",
    )
    if any(controls.get(key) is not False for key in prohibited):
        raise RuntimeError("publication rehearsal controls changed unexpectedly")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    import psycopg
    connection = psycopg.connect(dsn)
    try:
        connection.execute("BEGIN READ ONLY")
        active = connection.execute(
            """SELECT p.publication_id, p.content_fingerprint, p.record_count
               FROM presentation_active_publication a
               JOIN presentation_publications p ON p.publication_id=a.publication_id"""
        ).fetchone()
        if active is None:
            raise RuntimeError("no active presentation publication")
        active_id = str(active[0])
        active_fingerprint = str(active[1])
        active_record_count = int(active[2])
        if active_id != contract["expected_active_publication_id"]:
            raise RuntimeError(f"unexpected active publication: {active_id}")

        asset_rows = connection.execute(
            """SELECT DISTINCT asset_id FROM presentation_records
               WHERE publication_id=%s AND domain_id='metals' AND record_type='asset'
                 AND asset_id LIKE %s""",
            (active_id, "metals:vehicle:%"),
        ).fetchall()
        presentation_asset_ids = {str(row[0]) for row in asset_rows}

        history_rows = connection.execute(
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
    for ticker, observation_date, px in history_rows:
        ticker = str(ticker)
        series[ticker].append(float(px))
        dates[ticker] = str(observation_date)
    if set(series) != set(TICKERS):
        raise RuntimeError("market-history ticker coverage does not reconcile")

    candidate_records: list[dict[str, object]] = []
    for ticker in sorted(TICKERS):
        values = series[ticker]
        if len(values) < 500:
            raise RuntimeError(f"insufficient governed history for {ticker}")
        asset_id = f"metals:vehicle:{ticker}"
        if asset_id not in presentation_asset_ids:
            raise RuntimeError(f"active presentation asset missing: {asset_id}")
        state, evidence = state_for(values)
        candidate_records.append({
            "record_type": contract["presentation_record_type"],
            "domain_id": "metals",
            "asset_id": asset_id,
            "record_key": asset_id,
            "payload": {
                "ticker": ticker,
                "observation_date": dates[ticker],
                "market_state": state,
                "semantic_scope": contract["semantic_scope"],
                "evidence": evidence,
                "source_authority": contract["source_authority"],
                "tactical_posture": None,
                "cross_domain_rank": None,
                "automatic_execution_authorized": False,
            },
        })

    result = {
        "status": "PASS",
        "read_only": True,
        "contract_id": contract["contract_id"],
        "source_authority": contract["source_authority"],
        "presentation_record_type": contract["presentation_record_type"],
        "semantic_scope": contract["semantic_scope"],
        "candidate_record_count": len(candidate_records),
        "candidate_records": candidate_records,
        "active_publication_id_before": active_id,
        "active_publication_fingerprint_before": active_fingerprint,
        "active_publication_record_count_before": active_record_count,
        "active_publication_unchanged": True,
        "publication_projection_rehearsal_authorized": True,
        "presentation_activation_authorized": False,
        "production_database_write_executed": False,
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
