# Phase 3.1 — Universal Scoring Engine

## Objective

Create a deterministic, versioned, explainable, and asset-class-aware scoring framework that converts investment evidence into a common 0–100 scale.

## Build sequence

1. Phase 3.1.1 — Scoring contracts and architecture
2. Phase 3.1.2 — Normalization engine
3. Phase 3.1.3 — Weighted composite engine
4. Phase 3.1.4 — Asset-class profiles
5. Phase 3.1.5 — Explainability and diagnostics
6. Phase 3.1.6 — Registry and persistence
7. Phase 3.1.7 — Historical validation
8. Phase 3.1.8 — Certification

## Phase 3.1.1 acceptance criteria

- Scores are constrained to 0–100.
- Weights and confidence values are constrained to 0–1.
- Score bands cover 0–100 without gaps or overlaps.
- Universal dimensions are standardized.
- Profile weights total exactly 1.00 within tolerance.
- Missing, invalid, stale, insufficient-history, and not-applicable data are distinguishable.
- Contracts are immutable.
- Scoring profile and result versions are preserved.
- Tests pass before commit.
