from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_market_history_contract_is_fail_closed() -> None:
    payload = json.loads(
        (ROOT / "config/metals/market_history_authority_contract.json").read_text(encoding="utf-8")
    )
    assert payload["contract_id"] == "METALS-MARKET-HISTORY-1"
    assert payload["collection_period"] == "3y"
    assert payload["interval"] == "1d"
    assert payload["minimum_vehicle_rows_per_ticker"] == 500
    assert payload["minimum_benchmark_rows_per_symbol"] == 500
    assert payload["maximum_latest_market_age_days"] == 7
    assert payload["controls"] == {
        "production_database_write_authorized": False,
        "forecast_refresh_authorized": False,
        "model_retraining_authorized": False,
        "momentum_policy_authorized": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "missing_history_may_be_synthesized": False,
    }


def test_backfill_rehearsal_is_external_output_only_and_non_executing() -> None:
    source = (ROOT / "scripts/rehearse_metals_market_history_backfill.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--output-root", type=Path, required=True)' in source
    assert '"source": "yfinance"' in source
    assert '"production_database_write_authorized": False' in source
    assert '"forecast_refresh_authorized": False' in source
    assert '"model_retraining_authorized": False' in source
    assert '"momentum_policy_authorized": False' in source
    assert '"tactical_posture_authorized": False' in source
    assert '"automatic_execution_authorized": False' in source
    assert '"next_decision": "AUTHORIZE_METALS_MARKET_HISTORY_BACKFILL_INGESTION_REHEARSAL"' in source
    assert "psycopg" not in source
    assert "duckdb" not in source
    assert "UIIP_DATABASE_URL" not in source
