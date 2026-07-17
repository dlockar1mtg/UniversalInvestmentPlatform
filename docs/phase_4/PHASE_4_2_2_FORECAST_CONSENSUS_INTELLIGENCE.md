# Phase 4.2.2 — Forecast Consensus Intelligence

## Purpose

Phase 4.2.2 measures how strongly independent forecasting models agree for the
same asset, reference value, and forecast horizon.

## Components

- `ForecastConsensusInput`
- `ConsensusProfile`
- `ForecastConsensusEngine`
- `ForecastConsensusService`
- `ForecastConsensusResult`
- `ConsensusOutlier`
- `ConsensusStrength`

## Consensus score

The default score combines:

- Forecast-value agreement: 55%
- Directional agreement: 30%
- Model-quality agreement: 15%

Forecast-value agreement is derived from normalized forecast dispersion.
Directional agreement uses the dominant direction across models. Quality
agreement decreases when historical model-quality scores diverge.

## Outlier detection

The engine uses median absolute deviation to detect forecasts that materially
separate from the model group. Outliers reduce the final consensus score and
are listed in the consensus explanation.

## Confidence adjustment

Strong model agreement may increase forecast confidence. Weak or conflicted
agreement reduces confidence. The adjustment is bounded by the consensus
profile.

## Integration

`ForecastConsensusService` joins `UniversalForecast` records to the quality
scores created in Phase 4.2.1 before running consensus analysis.

This phase prepares the platform for quality-weighted ensemble forecasts.
