# Phase 4.4.4 — Forecast Drift Detection

## Purpose

Phase 4.4.4 detects when forecast models deteriorate or when a regime change
makes prior performance less reliable.

## Components

- `DriftDetectionProfile`
- `DriftMetric`
- `ForecastDriftSignal`
- `RegimePerformanceSnapshot`
- `DriftHistoryEntry`
- `DriftHistory`
- `ForecastDriftReport`
- `ForecastDriftDetectionEngine`
- `ForecastDriftDetectionService`
- Drift-history serialization helpers

## Drift dimensions

The engine compares baseline and current model scorecards across:

- Composite performance score
- Mean Absolute Error
- Absolute forecast bias
- Directional accuracy
- Prediction-interval calibration

## Regime awareness

A change between baseline and current regimes adds a configurable drift penalty
and creates regime-specific performance memory.

## Severity

Drift is classified as:

- None
- Low
- Moderate
- High
- Critical

## Recommendations

Depending on severity and current performance, the engine may recommend:

- No action
- Monitor
- Recalibrate
- Reduce model weight
- Retrain
- Retire

## Persistent history

Each drift run can be appended to persistent JSON history containing:

- Drift score
- Severity
- Recommendation
- Baseline and current regimes
- Normalized metric-level drift scores
- Evaluation timestamp

## Continuous-learning role

Phase 4.4.4 prevents the continuous-learning system from blindly trusting old
performance when model behavior or market structure has materially changed.

## Next phase

Phase 4.4.5 will implement forecast certification and production-readiness
governance.
