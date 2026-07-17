# Metals Data Flow

```text
External sources
(FRED, World Bank, EIA; optional market proxies)
        ↓
Collectors + ETL pipeline
        ↓
Raw/cache storage and collection audit tables
        ↓
Normalized observations and feature tables
        ↓
Metal scoring + macro regimes/scenarios
        ↓
Vehicle analytics and selection
        ↓
Portfolio targets/actions + risk + simulation
        ↓
Backtesting, attribution, confidence, grading
        ↓
Forecast ensemble (3/6/12/24 months)
        ↓
Uncertainty-adjusted expected-return views
        ↓
Decision support, opportunity rankings, platform health
        ↓
Monthly report + latest_* database views
        ↓
Native v8 CSV exports
        ↓
[Phase 1.2] Metals-to-Universal export adapter
        ↓
Universal staging, contract validation, manifest, ingestion
```

## Separation of responsibilities

The Metals platform determines metal-specific signals and decisions. The adapter only transforms, identifies, timestamps, validates, and packages those results. It must not recalculate scores or override recommendations.
