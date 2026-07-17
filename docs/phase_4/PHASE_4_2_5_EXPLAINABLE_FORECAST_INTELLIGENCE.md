# Phase 4.2.5 — Explainable Forecast Intelligence

## Purpose

Phase 4.2.5 converts forecast intelligence outputs into deterministic,
auditable explanations suitable for dashboards, reporting, validation, and
future recommendation workflows.

## Components

- `ForecastDriver`
- `ForecastRiskFactor`
- `HistoricalAnalog`
- `ForecastEvidenceGraph`
- `ForecastDriverAttributionEngine`
- `HistoricalSimilarityEngine`
- `ForecastEvidenceGraphBuilder`
- `ForecastNarrativeEngine`
- `ForecastExplanation`
- `ExplainableForecastIntelligenceService`
- Explanation JSON serializer

## Explanation inputs

The service combines:

- `UniversalForecast`
- Historical quality score
- Consensus score
- Calibrated confidence
- Optimized ensemble weights
- Forecast-driver contributions
- Risk factors
- Current normalized features
- Historical analog candidates

## Driver attribution

Raw signed contributions are normalized into importance shares. Drivers are
classified as positive, negative, or neutral and ranked deterministically.

## Historical analogs

Historical contexts are ranked using weighted normalized feature distance.
Each analog includes an overall similarity score, regime, outcome summary, and
feature-level similarity details.

## Evidence graph

The graph links the forecast to:

- Historical model quality
- Cross-model consensus
- Confidence calibration
- Ensemble model weights
- Forecast drivers
- Risk factors
- Historical analogs

## Narrative generation

The narrative engine is deterministic and rule-based. It identifies:

- Forecast direction and confidence
- Quality and consensus
- Leading ensemble model
- Strongest positive and negative drivers
- Principal unmitigated risk
- Closest historical analog

## Completion

This phase completes the Phase 4.2 Forecast Intelligence Layer and prepares the
platform for Phase 4.3 Universal Ensemble Forecast generation.
