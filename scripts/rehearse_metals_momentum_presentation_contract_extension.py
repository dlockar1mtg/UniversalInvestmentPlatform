from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.publication_model import (
    PresentationPublication,
    PresentationRecord,
    build_presentation_publication,
)
from foundation.presentation.publication_service import validate_publication_bundle
from scripts.certify_metals_current_momentum_states import TICKERS, state_for

CONTRACT_PATH = ROOT / "config" / "presentation" / "dash_read_1_metals_momentum_extension.json"
EXPECTED_BASE_RECORD_COUNT = 4171
EXPECTED_SOURCE_SHA256 = "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"
EXPECTED_ACTIVE_PUBLICATION_ID = "dash-read-1-metals-tactical-dff98e56d27c"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--expected-sha256", required=True)
    return parser.parse_args()


def _load_contract() -> dict[str, object]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("extension_id") != "DASH-READ-1-METALS-MOMENTUM-STATE":
        raise RuntimeError("unexpected Metals momentum presentation extension")
    if payload.get("version") != "1.0.0":
        raise RuntimeError("unsupported Metals momentum presentation extension version")
    controls = payload.get("controls") or {}
    if controls.get("presentation_contract_extension_authorized") is not True:
        raise RuntimeError("presentation contract extension is not authorized")
    prohibited = (
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "tactical_posture_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    )
    for key in prohibited:
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited presentation control changed unexpectedly: {key}")
    return payload


def _momentum_records(dsn: str, contract: dict[str, object]) -> list[PresentationRecord]:
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

    series: dict[str, list[float]] = {ticker: [] for ticker in TICKERS}
    dates: dict[str, str] = {}
    for ticker, observation_date, px in rows:
        ticker = str(ticker)
        if ticker not in series:
            raise RuntimeError(f"unexpected Metals history ticker: {ticker}")
        series[ticker].append(float(px))
        dates[ticker] = str(observation_date)

    if any(len(series[ticker]) < 500 for ticker in TICKERS):
        raise RuntimeError("insufficient governed market history for momentum presentation extension")

    records: list[PresentationRecord] = []
    for ticker in sorted(TICKERS):
        market_state, evidence = state_for(series[ticker])
        asset_id = f"metals:vehicle:{ticker}"
        payload = {
            "ticker": ticker,
            "observation_date": dates[ticker],
            "market_state": market_state,
            "semantic_scope": contract["semantic_scope"],
            "evidence": evidence,
            "source_authority": contract["source_authority"],
            "market_history_authority": contract["market_history_authority"],
            "tactical_posture": None,
            "cross_domain_rank": None,
            "automatic_execution_authorized": False,
        }
        records.append(
            PresentationRecord(
                record_type=str(contract["record_type"]),
                domain_id="metals",
                asset_id=asset_id,
                record_key=asset_id,
                payload=payload,
            )
        )
    return records


def main() -> int:
    args = parse_args()
    database = Path(args.database).resolve()
    expected_sha = args.expected_sha256.strip().lower()
    if expected_sha != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("unexpected analytical DuckDB SHA-256 authority")
    if not database.is_file():
        raise RuntimeError("analytical DuckDB is missing")

    dsn = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    contract = _load_contract()

    duck = duckdb.connect(str(database), read_only=True)
    try:
        base = build_presentation_publication(
            ROOT,
            database,
            duck,
            publication_id="dash-read-1-metals-momentum-extension-rehearsal",
            published_at_utc="2026-08-24T17:30:00+00:00",
        )
    finally:
        duck.close()

    validate_publication_bundle(base)
    if base.source_database_sha256 != expected_sha:
        raise RuntimeError("base presentation source SHA-256 changed")
    if len(base.records) != EXPECTED_BASE_RECORD_COUNT:
        raise RuntimeError(f"unexpected base presentation record count: {len(base.records)}")

    base_asset_ids = {
        item.asset_id
        for item in base.records
        if item.domain_id == "metals" and item.record_type == "asset" and item.asset_id is not None
    }
    momentum = _momentum_records(dsn, contract)
    expected_count = int(contract["expected_record_count"])
    if len(momentum) != expected_count:
        raise RuntimeError("momentum presentation record population does not reconcile")
    if len({item.asset_id for item in momentum}) != expected_count:
        raise RuntimeError("duplicate canonical asset IDs in momentum presentation extension")
    missing_assets = sorted(str(item.asset_id) for item in momentum if item.asset_id not in base_asset_ids)
    if missing_assets:
        raise RuntimeError(f"momentum records reference absent presentation assets: {missing_assets}")

    extended_records = tuple(sorted(
        tuple(base.records) + tuple(momentum),
        key=lambda item: (item.record_type, item.domain_id, item.asset_id or "", item.record_key),
    ))
    extended = replace(base, records=extended_records)
    validate_publication_bundle(extended)
    if len(extended.records) != EXPECTED_BASE_RECORD_COUNT + expected_count:
        raise RuntimeError("extended presentation record count does not reconcile")

    import psycopg
    pg = psycopg.connect(dsn)
    try:
        pg.execute("BEGIN READ ONLY")
        active = pg.execute(
            """SELECT p.publication_id, p.content_fingerprint, p.record_count
               FROM presentation_active_publication a
               JOIN presentation_publications p ON p.publication_id=a.publication_id"""
        ).fetchone()
        pg.rollback()
    finally:
        pg.close()
    if active is None:
        raise RuntimeError("no active presentation publication")
    active_id, active_fingerprint, active_record_count = str(active[0]), str(active[1]), int(active[2])
    if active_id != EXPECTED_ACTIVE_PUBLICATION_ID:
        raise RuntimeError(f"unexpected active presentation publication: {active_id}")
    if active_record_count != EXPECTED_BASE_RECORD_COUNT:
        raise RuntimeError("active presentation record count changed unexpectedly")

    result = {
        "status": "PASS",
        "read_only": True,
        "extension_id": contract["extension_id"],
        "source_authority": contract["source_authority"],
        "semantic_scope": contract["semantic_scope"],
        "presentation_record_type": contract["record_type"],
        "base_record_count": len(base.records),
        "momentum_record_count": len(momentum),
        "extended_record_count": len(extended.records),
        "extended_content_fingerprint": extended.content_fingerprint,
        "momentum_records": [item.canonical() for item in momentum],
        "active_publication_id_before": active_id,
        "active_publication_fingerprint_before": active_fingerprint,
        "active_publication_record_count_before": active_record_count,
        "active_publication_unchanged": True,
        "presentation_contract_extension_authorized": True,
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
