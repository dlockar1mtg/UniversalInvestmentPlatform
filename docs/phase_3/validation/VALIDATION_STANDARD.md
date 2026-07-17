# Historical Validation Standard

## Required records

### HistoricalObservation

Represents point-in-time data available on the observation date.

### PredictionRecord

Preserves the score, band, model identity, confidence, and coverage generated at time T.

### OutcomeRecord

Preserves the realized forward return, benchmark return, and downside outcome for a defined horizon.

### BacktestConfiguration

Defines the date range, model version, asset class, horizons, rebalance frequency, benchmark, filters, and warm-up window.

### ValidationResult

Stores metrics and pass/fail status for one model, backtest, and horizon.

## Anti-leakage rules

- A model must be resolved using the version effective on the prediction date.
- Features must carry point-in-time source and version metadata.
- Outcomes must occur strictly after predictions.
- Warm-up observations may inform features but may not be scored as validation predictions.
- Revised historical data must be versioned and distinguishable from originally available data.

## Baseline horizons

The first walk-forward engine should support configurable day horizons such as 30, 90, 180, 365, and 1,095 days.

## Scope boundary

Phase 3.2.1 defines contracts only. It does not yet execute backtests or calculate validation statistics.
