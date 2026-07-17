# Universal Scoring Standard

## Principle

Standardize the final score while preserving asset-specific evidence and normalization logic.

## Universal dimensions

- Return Potential
- Momentum
- Valuation
- Quality
- Risk
- Liquidity
- Diversification
- Macro Alignment
- Data Confidence

## Numeric ranges

- Metric and dimension scores: 0–100
- Weights: 0–1
- Confidence: 0–1
- Coverage ratio: 0–1

## Missing-data policy

A metric must declare one of these states:

- `available`
- `not_applicable`
- `unavailable`
- `invalid`
- `stale`
- `insufficient_history`

Only available metrics may contain a normalized score. Non-available metrics reduce coverage or confidence according to later engine policy; they do not automatically receive a score of zero.

## Versioning

Scoring profiles are immutable after use. Any material change to weights, dimensions, normalization, or risk policy requires a new profile version.

## Separation of concerns

The scoring engine classifies evidence. It does not issue buy, hold, sell, or rebalance instructions. Those actions belong to later recommendation and allocation engines.
