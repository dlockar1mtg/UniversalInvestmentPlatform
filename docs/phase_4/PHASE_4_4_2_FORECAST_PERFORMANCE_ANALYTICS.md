# Phase 4.4.2 — Forecast Performance Analytics

## Purpose

Phase 4.4.2 transforms archived forecast outcomes into model report cards and
deterministic performance rankings.

## Components

- `PerformanceAnalyticsProfile`
- `ForecastPerformanceMetrics`
- `ForecastPerformanceRankingEntry`
- `ForecastPerformanceReport`
- `ForecastPerformanceAnalyticsEngine`
- `ForecastPerformanceAnalyticsService`

## Metrics

The engine calculates:

- Mean Absolute Error
- Mean Squared Error
- Root Mean Squared Error
- Mean Absolute Percentage Error
- Symmetric Mean Absolute Percentage Error
- Mean signed bias
- Mean relative bias
- Directional accuracy
- Prediction-interval coverage
- Interval-coverage gap
- Scenario hit rate
- Composite performance score
- Qualitative performance grade

## Grouping

Performance may be evaluated by:

- Overall portfolio
- Model and model version
- Asset
- Forecast horizon

## Rolling windows

Optional rolling windows restrict analysis to outcomes observed within a
specified number of days before the evaluation date.

## Ranking

Scorecards are ranked deterministically using:

1. Eligibility
2. Higher composite score
3. Lower MAE
4. Larger sample size
5. Stable group key

## Continuous-learning role

These scorecards become the primary input for Phase 4.4.3 continuous model
learning and future adaptive model weighting.
