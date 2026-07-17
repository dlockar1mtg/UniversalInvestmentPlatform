# Phase 4.3.2 — Monte Carlo Simulation Engine

## Purpose

Phase 4.3.2 converts deterministic forecast assumptions into full terminal-value
probability distributions using reproducible Monte Carlo path simulation.

## Components

- `SimulationProcess`
- `MonteCarloSimulationProfile`
- `MonteCarloSimulationRequest`
- `MonteCarloDiagnostics`
- `MonteCarloSimulationResult`
- `MonteCarloSimulationEngine`
- `MonteCarloForecastService`

## Supported processes

- Geometric Brownian Motion
- Arithmetic Brownian Motion

Both processes use seeded NumPy random-number generation for deterministic,
reproducible simulation output.

## Distribution output

The engine produces the Phase 4.3.1 canonical distribution contract with:

- Terminal-value mean and median
- Variance and standard deviation
- Skewness and excess kurtosis
- Configurable percentiles
- Central confidence intervals
- Probability above or below the reference value
- Probability above a specified target value
- Lower-tail Value at Risk
- Lower-tail Expected Shortfall
- Probability of loss
- Probability of target shortfall

## Diagnostics

Simulation diagnostics include:

- Simulation count
- Number of time steps
- Random seed
- Invalid-value count
- Clipped-value count
- Terminal minimum and maximum
- Runtime
- Number of retained sample paths

## Path retention

Full path storage is disabled by default to avoid unnecessary memory use.
A bounded number of paths can be retained for diagnostics, charting, or future
scenario analysis.

## Next phase

Phase 4.3.3 will introduce Bayesian probability updating and posterior forecast
distributions that can be compared with and combined alongside Monte Carlo
results.
