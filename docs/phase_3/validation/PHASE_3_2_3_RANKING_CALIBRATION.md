# Phase 3.2.3 — Ranking and Calibration Metrics

## Objective

Measure whether higher model scores are associated with better future outcomes and whether score magnitudes are calibrated to realized results.

## Metrics

### Ranking

- Spearman rank correlation
- Kendall rank correlation

### Classification

- Hit rate
- Precision
- Recall
- False-positive rate
- False-negative rate

### Calibration

- Mean return by score band
- Median return by score band
- Hit rate by score band
- Quantile performance
- Top-versus-bottom spread
- Mean absolute calibration error

### Stability

- Correlation by horizon
- Mean correlation across horizons
- Minimum horizon correlation
- Ratio of horizons with positive correlation

## Important interpretation

A positive rank correlation means higher scores tended to correspond to better forward returns. It does not, by itself, prove economic significance or benchmark outperformance. Benchmark comparison is introduced in Phase 3.2.4.
