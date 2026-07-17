# Phase 4.2.1 — Forecast Quality and Model Ranking

## Purpose

Phase 4.2.1 creates the first reasoning layer above forecast execution. It
converts historical model evidence into comparable quality scores, ranks
candidate models, and produces an auditable model-selection decision.

## Components

- `ForecastModelEvidence`
- `ForecastQualityProfile`
- `ForecastQualityEngine`
- `ForecastModelRankingEngine`
- `ForecastModelSelectionService`
- `ForecastQualityScore`
- `ModelRankingEntry`
- `ModelSelectionResult`

## Scoring model

The default quality score combines:

- Accuracy: 35%
- Calibration: 25%
- Directional accuracy: 15%
- Stability: 15%
- Coverage: 10%

The raw score is adjusted for:

- Historical sample sufficiency
- Evidence freshness
- Forecast bias

## Selection behavior

Model evidence is filtered by asset class and forecast horizon. Eligible models
are ranked by adjusted score, raw score, sample size, and deterministic model
identity tie breakers. The top eligible model is selected with an auditable
selection explanation.

## Future use

Phase 4.2.2 will add consensus and disagreement analysis. Phase 4.2.3 will use
these quality scores as inputs to ensemble weighting.
