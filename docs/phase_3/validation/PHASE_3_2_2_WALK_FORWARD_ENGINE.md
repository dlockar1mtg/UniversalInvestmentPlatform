# Phase 3.2.2 — Walk-Forward Backtesting Engine

## Objective

Generate reproducible historical prediction and outcome datasets without look-ahead bias.

## Processing flow

1. Generate prediction dates from the configured rebalance frequency.
2. Apply the configured warm-up period.
3. Select the latest observation available on or before each prediction date.
4. Call the supplied point-in-time prediction function.
5. Apply score, confidence, and coverage filters.
6. Align each accepted prediction to one or more forward horizons.
7. Use the first observation on or after each target outcome date.
8. Calculate total return and maximum drawdown.
9. Preserve missing observations, filtered predictions, and missing outcomes in diagnostics.

## Anti-leakage behavior

The engine never selects an observation dated after the prediction date for prediction input. Outcome construction is separated from prediction generation and only accesses future data after a prediction has been frozen.

## Important scope boundary

The engine accepts a prediction callback. Phase 3.2.2 does not yet rebuild every historical scoring feature from source data. Asset-specific historical feature generation will be integrated in later cross-asset validation work.
