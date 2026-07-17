# Phase 4.2.3 — Adaptive Confidence Calibration

## Purpose

Phase 4.2.3 converts raw model confidence into evidence-based calibrated
confidence using historical reliability, consensus, market regime, sample
support, and evidence freshness.

## Components

- `MarketRegime`
- `ConfidenceCalibrationEvidence`
- `ConfidenceCalibrationRequest`
- `ConfidenceCalibrationProfile`
- `AdaptiveConfidenceCalibrationEngine`
- `ConfidenceCalibrationResult`
- `ForecastConfidenceCalibrationService`

## Calibration inputs

The engine evaluates:

- Raw model confidence
- Historical empirical success rate
- Historical reported confidence
- Calibration error
- Interval coverage
- Current consensus score
- Current model quality score
- Market-regime match
- Evidence sample size
- Evidence age

## Evidence selection

Calibration evidence must match:

- Forecast engine name and version
- Asset class
- Forecast horizon
- Evaluation date on or before the forecast date

Exact market-regime evidence is preferred. Unknown-regime evidence is used as
a fallback.

## Adjustment behavior

High historical reliability, strong consensus, fresh evidence, and exact regime
matching may increase confidence. Weak, stale, sparse, or mismatched evidence
reduces confidence. All adjustments are bounded by the calibration profile and
final confidence remains between zero and one.

## Integration

`ForecastConfidenceCalibrationService` applies the calibration result to an
immutable `UniversalForecast`, records the audit metadata, and appends the
calibration explanation to forecast notes.
