# Phase 3.1.6 — Explainability and Diagnostics

## Objective

Convert scoring internals into clear, deterministic, machine-readable explanations.

## Outputs

- Ranked dimension contributions
- Positive and negative drivers
- Confidence adjustment explanation
- Risk adjustment explanation
- Missing-data and omitted-dimension impacts
- Human-readable headline and summary
- Reproducibility audit record
- Stable JSON serialization

## Contribution logic

A dimension contribution equals:

`dimension score × normalized profile weight`

Contribution ranking explains which dimensions most influenced the raw composite score. Driver direction is determined from the underlying dimension score, not contribution size alone.

## Audit requirements

The audit record preserves:

- Asset identity
- Asset class
- Scoring date
- Model/profile identity and version
- Raw, confidence-adjusted, risk-adjusted, and final scores
- Coverage
- Dimension scores
- Effective dimension weights
- Omitted dimensions
- Warnings

## Scope boundary

This phase explains the score. It does not validate whether the score predicts future performance. Historical validation belongs to the next phase.
