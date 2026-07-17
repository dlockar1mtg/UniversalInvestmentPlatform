# Phase 4.3.1 — Forecast Distribution Framework

## Purpose

Phase 4.3.1 defines the canonical probability-distribution contract used by
Monte Carlo, Bayesian, scenario-tree, and other probabilistic forecast engines.

## Components

- `DistributionFamily`
- `DistributionStatus`
- `ForecastPercentile`
- `ForecastConfidenceInterval`
- `DistributionStatistics`
- `TailRiskMetrics`
- `DistributionProvenance`
- `ForecastDistributionResult`
- Distribution serialization and validation

## Contract capabilities

The framework supports:

- Mean, median, variance, and standard deviation
- Minimum, maximum, mode, skewness, and excess kurtosis
- Ordered percentile forecasts
- Central confidence intervals
- Lower- and upper-tail risk statistics
- Value at Risk and Expected Shortfall
- Probability of loss
- Probability of target shortfall
- Probability above the reference value
- Probability above a specified target value
- Model provenance and reproducibility metadata

## Validation safeguards

The contract verifies:

- Probability bounds
- Percentile uniqueness and monotonicity
- Confidence interval coverage
- Confidence interval and percentile consistency
- Median and 50th-percentile consistency
- Tail-risk direction consistency
- Target-probability dependencies
- Timezone-aware provenance
- Schema-version compatibility

## Serialization

The serializer recursively walks frozen dataclasses and immutable mappings. It
produces deterministic, JSON-safe output without relying on `dataclasses.asdict`
or deep-copying `MappingProxyType` values.

## Next phase

Phase 4.3.2 will use these contracts to implement deterministic Monte Carlo
path simulation, percentile extraction, confidence intervals, and tail-risk
analytics.
