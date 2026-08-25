from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

EXPECTED_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
KNOWN_SURFACES = (
    "metals_forecast_model_component_current",
    "metals_regime_probability_current",
    "metals_uncertainty_adjusted_view_current",
    "metals_recommendation_change_current",
    "metals_data_freshness_current",
    "metals_platform_health_current",
    "metals_tactical_state_current",
)
TARGET_HINTS = {
    "current_price": ("current_price", "price", "close", "latest_price", "spot_price"),
    "return_1m_pct": ("return_1m_pct",),
    "return_3m_pct": ("return_3m_pct",),
    "return_6m_pct": ("return_6m_pct",),
    "current_drawdown_pct": ("current_drawdown_pct", "drawdown"),
    "distance_ma50_pct": ("distance_ma50_pct",),
    "distance_ma200_pct": ("distance_ma200_pct",),
    "realized_volatility_3m_pct": ("realized_volatility_3m_pct", "volatility"),
    "candidate_regime": ("candidate_regime", "regime"),
    "tactical_state": ("tactical_state",),
    "forecast_point": ("point_forecast", "model_forecast", "forecast"),
    "forecast_expected_return": ("expected_return", "adjusted_expected_return", "raw_expected_return"),
    "forecast_lower_bound": ("lower_bound", "bear", "downside"),
    "forecast_upper_bound": ("upper_bound", "bull", "upside"),
    "rationale": ("rationale", "explanation", "message"),
    "risk": ("risk", "downside_penalty", "uncertainty_penalty"),
}


def columns(db: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    rows = db.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='main' AND table_name=? ORDER BY ordinal_position",
        [table],
    ).fetchall()
    return [str(row[0]) for row in rows]


def count_nonnull(db: duckdb.DuckDBPyConnection, table: str, column: str) -> tuple[int, int]:
    safe_table = '"' + table.replace('"', '""') + '"'
    safe_col = '"' + column.replace('"', '""') + '"'
    total, populated = db.execute(
        f"SELECT COUNT(*), COUNT({safe_col}) FROM {safe_table}"
    ).fetchone()
    return int(total), int(populated)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    path = Path(args.database)
    if not path.is_file():
        raise SystemExit(f"Database not found: {path}")

    db = duckdb.connect(str(path), read_only=True)
    try:
        all_tables = [str(row[0]) for row in db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name"
        ).fetchall()]
        metals_tables = [name for name in all_tables if name.startswith("metals_")]

        surface_report: dict[str, Any] = {}
        for table in KNOWN_SURFACES:
            cols = columns(db, table)
            if not cols:
                surface_report[table] = {"present": False, "columns": [], "row_count": 0}
                continue
            row_count = int(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            field_coverage = {}
            for col in cols:
                total, populated = count_nonnull(db, table, col)
                field_coverage[col] = {
                    "total": total,
                    "populated": populated,
                    "coverage_pct": None if total == 0 else round(100.0 * populated / total, 2),
                }
            surface_report[table] = {
                "present": True,
                "columns": cols,
                "row_count": row_count,
                "field_coverage": field_coverage,
            }

        candidate_sources: dict[str, list[dict[str, Any]]] = {key: [] for key in TARGET_HINTS}
        for table in metals_tables:
            cols = columns(db, table)
            lowered = {c.lower(): c for c in cols}
            for target, hints in TARGET_HINTS.items():
                for hint in hints:
                    matches = [orig for lower, orig in lowered.items() if hint in lower]
                    for column in matches:
                        total, populated = count_nonnull(db, table, column)
                        candidate_sources[target].append({
                            "table": table,
                            "column": column,
                            "total": total,
                            "populated": populated,
                            "coverage_pct": None if total == 0 else round(100.0 * populated / total, 2),
                        })

        for target in candidate_sources:
            candidate_sources[target].sort(
                key=lambda row: (
                    -(row["coverage_pct"] if row["coverage_pct"] is not None else -1),
                    row["table"],
                    row["column"],
                )
            )

        tactical_rows = []
        if columns(db, "metals_tactical_state_current"):
            wanted = [
                "universal_asset_id", "ticker", "state_available", "candidate_regime", "tactical_state",
                "return_1m_pct", "return_3m_pct", "return_6m_pct", "distance_ma50_pct",
                "distance_ma200_pct", "current_drawdown_pct", "realized_volatility_3m_pct",
                "is_reference_control",
            ]
            tactical_rows = [dict(zip(wanted, row)) for row in db.execute(
                "SELECT " + ",".join(wanted) + " FROM metals_tactical_state_current ORDER BY universal_asset_id"
            ).fetchall()]

        report = {
            "status": "PASS",
            "read_only": True,
            "database": str(path),
            "known_surface_report": surface_report,
            "candidate_sources_by_dashboard_field": candidate_sources,
            "tactical_asset_rows": tactical_rows,
            "metals_table_count": len(metals_tables),
            "metals_tables": metals_tables,
            "next_decision": "DESIGN_METALS_PRESENTATION_DATA_COMPLETENESS_REMEDIATION",
        }
        text = json.dumps(report, indent=2, default=str)
        print(text)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
    finally:
        db.close()


if __name__ == "__main__":
    main()
