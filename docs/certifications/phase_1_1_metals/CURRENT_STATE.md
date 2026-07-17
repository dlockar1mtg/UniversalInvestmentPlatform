# Metals Platform Current State — Frozen Baseline

## Release identity

- Latest stable release stated by the project: **v8.1**
- Operational status: **Production Stable**
- Database engine: **DuckDB**
- Main database: `data/metals_intelligence.duckdb`
- Primary configuration: `config/settings.yaml`
- Primary v8 orchestrator: `run_v8_pipeline.py`
- Historical collection entry point: `run_platform.py`

## Repository profile

The archive contains a mature Python application organized around collection, analytics, macro modeling, portfolio construction, risk, vehicle selection, backtesting, decision support, forecasting, reporting, and dashboard generation. The core application code is under `metals_platform/`; versioned root scripts act as installers, migrations, runners, exporters, inspectors, and repairs.

## Current analytical scope

The configured metal universe is gold, silver, platinum, copper, aluminum, nickel, zinc, tin, and uranium. Gold, silver, and platinum are strategic assets; copper and uranium are tactical assets; aluminum, nickel, zinc, and tin are research-only in the current investability configuration.

## Current v8 outputs

The active v8 export layer writes nine CSV files from `latest_*` DuckDB views and generates a monthly HTML committee report. These outputs cover forecasts, model components, learned regimes, uncertainty-adjusted views, opportunity rankings, recommendation changes, freshness, platform health, and report metadata.

## Frozen constraints

1. Universal integration must not alter Metals scoring, forecasting, risk, optimization, or recommendation logic during Phase 1.
2. The DuckDB schema is internal implementation detail, not the permanent cross-platform API.
3. Existing v8 CSVs may be read by an adapter, but their native schemas are not themselves the Universal contracts.
4. Secrets in `.env` are excluded from all integration copies and manifests.
5. Historical upgrade, repair, and legacy export scripts remain available but are not part of the supported Phase 1 runtime.

## Known limitations

- No Universal export adapter exists yet.
- No Universal registry record is emitted by Metals.
- Native identifiers are metal names and tickers rather than Universal `asset_id` values.
- The current v8 export set does not directly emit a complete Universal `asset_master`, `portfolio_positions`, or `risk_metrics` file.
- The regime model is a transparent volatility-state approximation rather than a full hidden Markov model.
- The monthly committee report is HTML rather than PDF.

This document freezes the supplied repository as the Phase 1.1 baseline.
