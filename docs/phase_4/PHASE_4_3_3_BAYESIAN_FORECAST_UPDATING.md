# Phase 4.3.3 — Bayesian Forecast Updating

## Purpose

Phase 4.3.3 updates forecast probability distributions as new evidence arrives
without requiring the underlying forecast model to be retrained.

## Components

- `BayesianUpdateFamily`
- `NormalPrior`
- `NormalEvidence`
- `BetaPrior`
- `BinomialEvidence`
- `BayesianUpdateRequest`
- `BayesianUpdateDiagnostics`
- `BayesianUpdateResult`
- `BayesianForecastUpdateEngine`
- `BayesianForecastUpdateService`

## Supported update families

### Normal-Normal

Used for continuous forecast values where:

- The prior is normal
- New evidence is summarized by a sample mean
- Observation variance is known or supplied
- Evidence may be weighted

The posterior mean is precision weighted, and posterior variance contracts as
evidence accumulates.

### Beta-Binomial

Used for binary-event probabilities where:

- The prior is beta distributed
- New evidence is represented by successes and trials
- Evidence may be fractionally weighted

Posterior alpha and beta are updated directly from weighted successes and
failures.

## Outputs

Both update families emit the canonical Phase 4.3.1
`ForecastDistributionResult` with:

- Posterior mean and variance
- Percentiles
- Credible intervals
- Probability above the reference value
- Probability above a target
- Lower-tail risk metrics
- Reproducibility provenance
- Update diagnostics and explanations

## Integration

`BayesianForecastUpdateService` converts a `UniversalForecast` into either:

- A continuous posterior-value distribution
- A posterior probability distribution

## Next phase

Phase 4.3.4 will build scenario-tree generation on top of Monte Carlo and
Bayesian posterior distributions.
