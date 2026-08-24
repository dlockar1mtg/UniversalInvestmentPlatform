from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def scalar(connection, sql: str, params=()):
    return connection.execute(sql, list(params)).fetchone()[0]


def rows(connection, sql: str, params=()):
    cursor = connection.execute(sql, list(params))
    names = [str(item[0]) for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of Metals tactical-decision depth in current UIP authority."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--expected-sha256", default=None)
    args = parser.parse_args()

    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"Database not found: {database}")

    import hashlib

    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    if args.expected_sha256 and digest.lower() != args.expected_sha256.lower():
        raise SystemExit(
            f"Database SHA mismatch: expected {args.expected_sha256}, found {digest}"
        )

    connection = duckdb.connect(str(database), read_only=True)
    try:
        recommendation_count = scalar(
            connection,
            "SELECT COUNT(*) FROM recommendations_current WHERE lower(platform_id)='metals'",
        )
        forecast_count = scalar(
            connection,
            "SELECT COUNT(*) FROM forecasts_current WHERE lower(platform_id)='metals'",
        )
        risk_count = scalar(
            connection,
            "SELECT COUNT(*) FROM risk_metrics_current WHERE lower(platform_id)='metals'",
        )
        asset_count = scalar(
            connection,
            "SELECT COUNT(*) FROM asset_master_current WHERE lower(platform_id)='metals'",
        )

        horizons = rows(
            connection,
            """
            SELECT forecast_horizon_months AS horizon_months,
                   COUNT(*) AS rows,
                   COUNT(expected_return) AS expected_return_populated,
                   COUNT(probability_positive) AS probability_positive_populated,
                   COUNT(confidence_score) AS confidence_populated,
                   COUNT(point_forecast) AS point_forecast_populated,
                   COUNT(lower_bound) AS lower_bound_populated,
                   COUNT(upper_bound) AS upper_bound_populated,
                   COUNT(scenario) AS scenario_populated
            FROM forecasts_current
            WHERE lower(platform_id)='metals'
            GROUP BY forecast_horizon_months
            ORDER BY forecast_horizon_months
            """,
        )

        forecast_assets = rows(
            connection,
            """
            SELECT a.universal_asset_id,
                   a.asset_name,
                   a.asset_symbol,
                   string_agg(CAST(f.forecast_horizon_months AS VARCHAR), ',' ORDER BY f.forecast_horizon_months) AS horizons,
                   COUNT(*) AS forecast_rows,
                   COUNT(f.expected_return) AS expected_return_populated,
                   COUNT(f.probability_positive) AS probability_positive_populated,
                   COUNT(f.confidence_score) AS confidence_populated
            FROM forecasts_current f
            LEFT JOIN asset_master_current a
              ON a.universal_asset_id=f.universal_asset_id
             AND lower(a.platform_id)='metals'
            WHERE lower(f.platform_id)='metals'
            GROUP BY a.universal_asset_id, a.asset_name, a.asset_symbol
            ORDER BY a.universal_asset_id
            """,
        )

        recommendation_assets = rows(
            connection,
            """
            SELECT r.universal_asset_id,
                   a.asset_name,
                   a.asset_symbol,
                   r.recommendation,
                   r.normalized_score,
                   r.confidence_score,
                   r.time_horizon_months,
                   CASE WHEN r.rationale IS NULL OR trim(CAST(r.rationale AS VARCHAR))='' THEN FALSE ELSE TRUE END AS rationale_available,
                   CASE WHEN r.risk_summary IS NULL OR trim(CAST(r.risk_summary AS VARCHAR))='' THEN FALSE ELSE TRUE END AS risk_summary_available,
                   CASE WHEN f.universal_asset_id IS NULL THEN FALSE ELSE TRUE END AS forecast_available,
                   CASE WHEN k.universal_asset_id IS NULL THEN FALSE ELSE TRUE END AS risk_available
            FROM recommendations_current r
            LEFT JOIN asset_master_current a
              ON a.universal_asset_id=r.universal_asset_id
             AND lower(a.platform_id)='metals'
            LEFT JOIN (SELECT DISTINCT universal_asset_id FROM forecasts_current WHERE lower(platform_id)='metals') f
              ON f.universal_asset_id=r.universal_asset_id
            LEFT JOIN (SELECT DISTINCT universal_asset_id FROM risk_metrics_current WHERE lower(platform_id)='metals') k
              ON k.universal_asset_id=r.universal_asset_id
            WHERE lower(r.platform_id)='metals'
            ORDER BY r.universal_asset_id
            """,
        )

        risk_coverage = rows(
            connection,
            """
            SELECT COUNT(*) AS rows,
                   COUNT(risk_score) AS risk_score,
                   COUNT(risk_level) AS risk_level,
                   COUNT(volatility) AS volatility,
                   COUNT(downside_volatility) AS downside_volatility,
                   COUNT(maximum_drawdown) AS maximum_drawdown,
                   COUNT(value_at_risk) AS value_at_risk,
                   COUNT(expected_shortfall) AS expected_shortfall,
                   COUNT(beta) AS beta,
                   COUNT(liquidity_score) AS liquidity_score,
                   COUNT(concentration_score) AS concentration_score
            FROM risk_metrics_current
            WHERE lower(platform_id)='metals'
            """,
        )[0]

        report = {
            "status": "PASS",
            "read_only": True,
            "database_sha256": digest,
            "population": {
                "assets": asset_count,
                "recommendations": recommendation_count,
                "forecasts": forecast_count,
                "risk_rows": risk_count,
            },
            "forecast_horizon_coverage": horizons,
            "forecast_asset_coverage": forecast_assets,
            "recommendation_asset_coverage": recommendation_assets,
            "risk_metric_coverage": risk_coverage,
            "tactical_decision_target": {
                "strategic_thesis": "12-24m+ context",
                "medium_term_opportunity": "6-24m expected return and probability-positive",
                "momentum_regime": "requires first-class promotion of Metals-native regime/model evidence",
                "tactical_posture": "requires separately governed Metals-native decision policy",
                "current_value_and_history": "must be certified before entry/exit price visuals",
            },
        }
        print(json.dumps(report, indent=2, default=str))
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
