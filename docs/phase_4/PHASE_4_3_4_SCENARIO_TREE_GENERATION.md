# Phase 4.3.4 — Scenario Tree Generation

## Purpose

Phase 4.3.4 creates auditable multi-stage scenario trees and converts their
terminal paths into canonical probability distributions.

## Components

- `ScenarioDirection`
- `ScenarioBranchTemplate`
- `ScenarioStageDefinition`
- `ScenarioTreeProfile`
- `ScenarioTreeRequest`
- `ScenarioTreeNode`
- `ScenarioTerminalOutcome`
- `ScenarioTreeDiagnostics`
- `ScenarioTreeResult`
- `ScenarioTreeGenerationEngine`
- `ScenarioTreeForecastService`

## Tree generation

Each stage contains mutually exclusive branches whose probabilities sum to one.
The engine generates the Cartesian product of all stage branches, producing
complete terminal paths with:

- Conditional branch probabilities
- Cumulative path probabilities
- Compounded terminal values
- Total returns
- Aggregated direction labels

## Pruning

The tree may be reduced using:

- Minimum path probability
- Maximum terminal-path count
- Optional probability renormalization

Generation fails when pruning removes every terminal path.

## Distribution output

The retained terminal paths are converted into the canonical
`ForecastDistributionResult` with:

- Probability-weighted expected value
- Weighted variance and standard deviation
- Weighted percentiles
- Central confidence intervals
- Probability of gain or loss
- Probability of exceeding a target
- Value at Risk
- Expected Shortfall
- Skewness and excess kurtosis

## Auditability

The result retains both the full node graph and terminal path records, allowing
dashboards and validation tools to explain exactly how every scenario outcome
was constructed.

## Next phase

Phase 4.3.5 will add distribution-level risk analytics and uncertainty
decomposition across Monte Carlo, Bayesian, and scenario-tree outputs.
