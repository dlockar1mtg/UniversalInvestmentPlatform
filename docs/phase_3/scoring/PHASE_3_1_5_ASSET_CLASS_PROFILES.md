# Phase 3.1.5 — Asset-Class Scoring Profiles

## Objective

Define the first active scoring configurations for crypto, ETFs, metals, MTG sealed collectibles, housing markets, and cash equivalents.

## Design

Each profile contains:

- Model ID
- Scoring profile ID and version
- Normalization profile ID
- Universal dimension weights
- Coverage threshold
- Confidence floor
- Maximum risk penalty
- Metric-level normalization rules
- Metric-level weights and default confidence

## Important limitation

These are baseline version 1 profiles. Their weights and thresholds are architectural defaults, not historically validated optimal settings. Historical calibration and performance validation remain part of later phases.

## Activated models

The scoring model registry entries become active on July 17, 2026 after these profiles are installed and certified.

## Supported classes

- Crypto
- ETF
- Metals
- MTG
- Housing
- Cash
