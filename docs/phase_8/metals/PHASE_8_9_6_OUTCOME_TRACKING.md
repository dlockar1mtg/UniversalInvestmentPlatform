# Phase 8.9.6 — Metals Out-of-Sample Outcome Tracking

## Objective

Connect matured Metals forecasts and recommendations to measurable realized outcomes without altering the preserved forecasting models.

## Metrics

The outcome engine records:

- absolute forecast error;
- root-mean-squared forecast error;
- directional accuracy;
- probability calibration error;
- recommendation hit rate;
- post-signal return;
- excess return versus benchmark;
- regime performance;
- estimated vehicle slippage;
- net return after slippage;
- portfolio contribution.

## Input contract

The CSV input requires:

- `forecast_id`
- `asset_id`
- `vehicle_ticker`
- `horizon_days`
- `forecast_return_pct`
- `forecast_probability_up`
- `recommendation`
- `signal_price`
- `realized_price`
- `benchmark_return_pct`
- `regime`
- `portfolio_weight_pct`
- `estimated_slippage_pct`

Forecast identifiers must be unique. Horizons and prices must be positive. Probabilities must be between zero and one. Unsupported recommendation labels fail closed.

## Runtime input

The default production input is:

`data/operations/metals/outcome_tracking_input.csv`

A deterministic certification sample is stored at:

`config/metals/outcome_tracking_validation_sample.csv`

The validation sample certifies the evaluator and publisher only. It is not represented as historical live performance.

## Outputs

The publisher writes:

- `metals_outcome_summary.json`
- `metals_outcomes.json`
- `metals_outcomes.csv`
- `metals_regime_performance.json`

under:

`data/operations/metals/outcome_tracking/`

## Commands

Focused validation:

```powershell
python -m pytest tests\production\test_metals_outcome_tracking.py -q
```

Certification-sample publication:

```powershell
python scripts\publish_metals_outcome_tracking.py `
  --input config\metals\outcome_tracking_validation_sample.csv `
  --strict
```

Production publication:

```powershell
python scripts\publish_metals_outcome_tracking.py --strict
```

Production strict mode returns nonzero when no matured-outcome input is available. This prevents an empty outcome history from being certified as live performance.
