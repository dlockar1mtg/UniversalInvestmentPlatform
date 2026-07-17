# Phase 3.2.4 — Benchmark Comparison Engine

## Objective

Measure model performance relative to an appropriate asset-class benchmark.

## Metrics

- Mean model return
- Mean benchmark return
- Mean excess return
- Benchmark win rate
- Alpha
- Beta
- Tracking error
- Information ratio
- Upside capture
- Downside capture
- Relative maximum drawdown

## Benchmark registry

Configured asset-class benchmarks include:

- Crypto: Bitcoin
- ETF: VOO
- Metals: GLD
- MTG: Internal equal-weight MTG index
- Housing: National housing index
- Cash: BIL

## Interpretation

Positive excess return indicates that the model outperformed its benchmark over the measured sample. Alpha and information ratio should be interpreted cautiously when samples are small or overlapping. These metrics demonstrate relative performance but do not eliminate transaction-cost, tax, survivorship, or implementation concerns.
