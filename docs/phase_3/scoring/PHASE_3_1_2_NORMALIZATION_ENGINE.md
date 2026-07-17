# Phase 3.1.2 — Universal Score Normalization Engine

## Objective

Convert heterogeneous investment metrics into deterministic 0–100 scores while preserving diagnostics, missing-data states, and raw values.

## Strategies

- Higher is better
- Lower is better
- Bounded range
- Target centered
- Percentile
- Binary
- Categorical
- Piecewise linear

## Design rules

- Use `Decimal` for numeric calculations.
- Do not convert missing data into zero.
- Out-of-range values may be clipped only when configured.
- Every normalization returns diagnostics.
- Strategy behavior must remain deterministic and independently testable.
- Asset-specific configuration belongs outside the strategy implementation.

## Certification

Run:

```powershell
python scripts\certify_phase_3_1_2.py
```
