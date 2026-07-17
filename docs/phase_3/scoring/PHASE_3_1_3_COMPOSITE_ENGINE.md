# Phase 3.1.3 — Weighted Composite Scoring Engine

## Objective

Combine normalized metric components into dimension scores and a final universal investment score.

## Calculation order

1. Aggregate available metric scores within each dimension.
2. Measure dimension coverage.
3. Reweight usable profile dimensions.
4. Calculate the raw composite score.
5. Calculate weighted confidence.
6. Apply the profile confidence floor.
7. Apply the risk penalty.
8. Quantize the final score to two decimal places.
9. Assign the universal score band.
10. Preserve intermediate diagnostics.

## Missing-data behavior

- `not_applicable` metrics are excluded from coverage.
- Other unavailable states reduce coverage.
- Missing metrics do not automatically receive a zero score.
- A dimension with no available metrics is omitted and remaining usable dimensions are proportionally reweighted.
- The engine fails when no dimensions are scorable.

## Risk interpretation

The Risk dimension is encoded so that a higher score means safer or more favorable risk characteristics. Therefore, lower risk scores produce larger penalties.

## Separation of concerns

This engine creates scores and diagnostic drivers. It does not issue trade recommendations.
