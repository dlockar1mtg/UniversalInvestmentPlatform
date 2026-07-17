# Metals Database Map

The supplied DuckDB contains **72 base tables** and **48 views**. Full object names, row counts, column counts, and column definitions are in `DATABASE_INVENTORY.csv`.

## Functional table groups

- Collection and quality: `collection_runs`, `collection_results`, `series_catalog`, `observations`, `data_quality_results`, `data_freshness_details`
- Features and scoring: `monthly_features`, `ratio_features`, `metal_scores`, `analytics_runs`, `allocation_recommendations`
- Macro intelligence: `macro_runs`, `macro_regimes`, `macro_scenarios`, `macro_monthly_features`, probability tables, `metal_macro_scores`
- Vehicle intelligence: vehicle catalog, prices, metrics, recommendations, simulation status, advanced metrics
- Portfolio and execution: portfolio runs, positions, targets, actions, reserve ledger, cash audit, trade queue
- Risk and simulation: risk runs, contributions, stress tests, simulation results and percentiles
- Optimization: optimization runs, expected returns, Black-Litterman outputs, optimized weights, uncertainty-adjusted views
- Validation: backtest runs/results/summary, walk-forward weights, institutional metrics
- Attribution and confidence: attribution runs/returns, performance attribution, confidence scores, component grades
- Decision support: decision runs, recommendation history/alerts/change explanations, opportunity rankings, platform health, committee summary
- Forecasting/reporting: forecast runs, forecasts, model components, learned regime probabilities, committee reports

## Integration rule

Universal production ingestion must not query these tables directly. The database may be used during development to verify lineage and reconciliation, but the durable interface is a versioned export package.
