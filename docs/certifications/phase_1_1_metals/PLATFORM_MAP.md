# Metals Platform Map

## Important directories

```text
metals/
├── config/                  Runtime settings, series definitions, holdings
├── data/
│   ├── metals_intelligence.duckdb
│   ├── backups/             Database safety copies
│   ├── exports/             Current CSV and HTML deliverables
│   ├── logs/                Runtime logs
│   └── raw/                 Collected source material
├── docs/                    Current-state documentation
├── metals_platform/
│   ├── collectors/          External-source collection
│   ├── etl/                 Collection orchestration
│   ├── database/            Schema, migrations, views, DB wrapper
│   ├── analytics/           Features, scoring, allocation analytics
│   ├── macro/               Regimes, scenarios, probabilities
│   ├── vehicles/            ETFs/vehicles, prices, metrics, selection
│   ├── portfolio/           Holdings, targets, actions, simulation
│   ├── risk/                Risk and stress calculations
│   ├── optimizer/           Black-Litterman and uncertainty views
│   ├── backtest/            Historical validation
│   ├── attribution/         Performance attribution
│   ├── confidence/          Dynamic confidence and grading
│   ├── decision_support/    Recommendations, rankings, health
│   ├── forecasting/         Multi-horizon forecast ensemble
│   ├── reporting/           Monthly committee report
│   └── dashboard/           HTML/data explorer outputs
├── tests/                   Automated unit/integration tests
├── run_*.py                 Operational entry points
├── export_*.py              Versioned exports
├── apply_*.py               Upgrades and schema/config migrations
└── inspect_*.py             Validation and diagnostics
```

## Supported Phase 1 components

Supported: `run_v8_pipeline.py`, v8 engines it invokes, `export_v8.py`, active database views, configuration required for those engines, and the nine v8 CSV exports.

Reference-only: earlier v5-v7 orchestrators, installers, patches, repair scripts, compiled bytecode, backups, and legacy exports.

## Architectural classification

Metals is a standalone domain platform. It owns domain collection and modeling. The Universal platform owns cross-platform identifiers, contract validation, manifests, ingestion, comparison, and portfolio-level aggregation.
