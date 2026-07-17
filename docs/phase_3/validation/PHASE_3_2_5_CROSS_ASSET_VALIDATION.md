# Phase 3.2.5 — Cross-Asset Validation

## Objective

Compare scoring-model validation quality across crypto, ETFs, metals, MTG, housing, and cash using a common framework.

## Standardized inputs

Each asset-class summary contains:

- Observation count
- Asset count
- Coverage ratio
- Spearman and Kendall correlation
- Hit rate
- Top-versus-bottom spread
- Mean benchmark excess return
- Information ratio
- Benchmark win rate
- Calibration error
- Asset-class limitations

## Composite grading

The version 1 cross-asset grade combines normalized:

- Spearman correlation: 20%
- Hit rate: 15%
- Top-bottom spread: 15%
- Excess return: 15%
- Information ratio: 15%
- Benchmark win rate: 10%
- Calibration quality: 10%

Coverage, sample size, and asset breadth may reduce the final grade.

## Important limitation

Cross-asset grades compare validation quality, not expected investment return. An A-grade cash model does not imply that cash should outperform an A-grade crypto model. It means the scoring model demonstrates stronger evidence relative to its own objectives and benchmark.

The version 1 grading transformations are architectural defaults and require later empirical calibration.
