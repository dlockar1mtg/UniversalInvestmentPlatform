# Phase 4.3.5 — Distribution Risk Analytics

## Purpose

Phase 4.3.5 provides one shared risk-intelligence layer for canonical forecast
distributions produced by Monte Carlo, Bayesian, and scenario-tree engines.

## Components

- `DistributionRiskGrade`
- `DistributionRiskProfile`
- `TailRiskPoint`
- `DistributionRiskMetrics`
- `DistributionComparisonEntry`
- `DistributionComparisonResult`
- `DistributionRiskAnalyticsEngine`
- `DistributionRiskAnalyticsService`

## Analytics

The engine calculates:

- Expected and median return
- Distribution volatility
- Probability of loss
- Downside probability
- Upside probability
- Target-attainment probability
- Downside deviation
- Upside potential
- Confidence-interval width
- Normalized uncertainty width
- Distribution asymmetry
- Tail concentration
- Risk-adjusted expected return
- Multi-level Value at Risk
- Multi-level Expected Shortfall
- Composite risk score and risk grade

## Input support

The engine can use:

- Explicit terminal-value samples
- Explicit probability weights
- Canonical distribution percentiles as an approximation when raw samples are
  unavailable

## Comparison

Multiple distributions can be ranked deterministically using:

1. Lower composite risk score
2. Higher risk-adjusted return
3. Higher expected return
4. Stable asset and distribution identifiers

## Next phase

Phase 4.3.6 will unify Monte Carlo, Bayesian, and scenario-tree outputs into one
probabilistic forecast orchestration service.
