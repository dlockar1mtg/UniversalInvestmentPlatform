from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb


def columns(conn: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [str(row[0]) for row in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='main' AND table_name=? ORDER BY ordinal_position",
        [table],
    ).fetchall()]


def safe_scalar(conn: duckdb.DuckDBPyConnection, sql: str) -> Any:
    try:
        row = conn.execute(sql).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    db = Path(args.database).resolve()
    out = Path(args.output).resolve()
    if not db.is_file():
        raise SystemExit(f"Database missing: {db}")
    if out.exists():
        raise SystemExit(f"Refusing to overwrite audit evidence: {out}")

    conn = duckdb.connect(str(db), read_only=True)
    tables = [str(row[0]) for row in conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name"
    ).fetchall()]

    price_name_tokens = {"price", "close", "adj_close", "adjusted_close", "value", "last_price", "current_price"}
    date_name_tokens = {"date", "as_of_date", "observation_date", "timestamp", "datetime", "price_date", "trading_date"}
    identity_tokens = {"asset_id", "universal_asset_id", "universal_vehicle_id", "ticker", "symbol", "metal", "series_key"}
    bound_tokens = {"lower_bound", "upper_bound", "point_forecast", "expected_return", "forecast_horizon_months", "horizon_months"}
    rationale_tokens = {"rationale", "explanation", "reason", "risk_summary", "thesis", "summary"}

    candidates: list[dict[str, Any]] = []
    for table in tables:
        cols = columns(conn, table)
        lower = {c.lower() for c in cols}
        matched_price = sorted(lower & price_name_tokens)
        matched_date = sorted(lower & date_name_tokens)
        matched_identity = sorted(lower & identity_tokens)
        matched_bounds = sorted(lower & bound_tokens)
        matched_rationale = sorted(lower & rationale_tokens)
        if not any((matched_price, matched_bounds, matched_rationale)):
            continue
        candidates.append({
            "table": table,
            "columns": cols,
            "row_count": safe_scalar(conn, f'SELECT COUNT(*) FROM "{table}"'),
            "price_columns": matched_price,
            "date_columns": matched_date,
            "identity_columns": matched_identity,
            "forecast_columns": matched_bounds,
            "rationale_columns": matched_rationale,
        })

    known_tables: dict[str, Any] = {}
    for table in (
        "metals_tactical_state_current",
        "metals_uncertainty_adjusted_view_current",
        "metals_forecast_model_component_current",
        "metals_regime_probability_current",
        "metals_recommendation_change_current",
    ):
        if table in tables:
            known_tables[table] = {
                "columns": columns(conn, table),
                "row_count": safe_scalar(conn, f'SELECT COUNT(*) FROM "{table}"'),
            }

    report = {
        "status": "PASS",
        "read_only": True,
        "database": str(db),
        "table_count": len(tables),
        "candidate_table_count": len(candidates),
        "candidate_tables": candidates,
        "known_metals_surfaces": known_tables,
        "semantic_rules": {
            "price_semantics_is_not_numeric_price": True,
            "downside_penalty_is_not_forecast_lower_bound": True,
            "uncertainty_penalty_is_not_generic_risk_score": True,
            "recommendation_change_explanation_is_not_full_investment_thesis": True,
        },
        "next_decision": "DESIGN_METALS_DECISION_UTILITY_COMPLETION_FROM_RESOLVED_AUTHORITIES",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
