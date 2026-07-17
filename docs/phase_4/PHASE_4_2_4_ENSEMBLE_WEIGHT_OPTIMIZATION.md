# Phase 4.2.4 — Ensemble Weight Optimization

## Purpose

Phase 4.2.4 assigns dynamic normalized weights to eligible forecasting models
using outputs from quality ranking, consensus intelligence, and adaptive
confidence calibration.

## Components

- `EnsembleWeightProfile`
- `EnsembleModelSignal`
- `EnsembleWeightEntry`
- `EnsembleWeightResult`
- `EnsembleWeightOptimizationEngine`
- `EnsembleWeightOptimizationService`

## Default weighting factors

- Historical model quality: 35%
- Calibrated confidence: 25%
- Consensus alignment: 20%
- Historical reliability: 15%
- Market-regime match: 5%

## Constraints

The optimizer:

- Excludes ineligible models by default
- Requires at least two eligible models
- Normalizes model weights to one
- Applies configurable minimum and maximum model weights
- Redistributes excess or deficit weight across eligible models
- Uses equal weights only when every optimization signal is zero

## Integration

`EnsembleWeightOptimizationService` joins:

- `UniversalForecast`
- `ForecastQualityScore`
- `ConfidenceCalibrationResult`
- `ForecastConsensusResult`

It then calculates each model's alignment to the consensus value and produces
an auditable, constrained ensemble weight allocation.

This phase prepares the platform for Phase 4.3, where the optimized weights
will be used to produce a combined ensemble forecast.
