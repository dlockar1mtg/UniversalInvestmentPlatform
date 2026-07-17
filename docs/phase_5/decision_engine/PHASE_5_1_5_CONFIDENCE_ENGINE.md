# Phase 5.1.5 — Universal Confidence Aggregation Engine

## Objective

Calculate how certain the platform is about an investment recommendation
independently from the opportunity score.

## Score versus confidence

The decision score measures investment attractiveness.

Confidence measures the strength, consistency, and reliability of the
information supporting that assessment.

A high score does not necessarily imply high confidence.

## Default confidence components

| Component | Weight |
|---|---:|
| Forecast confidence | 25% |
| Historical reliability | 25% |
| Data quality | 20% |
| Evidence quality | 15% |
| Evidence consistency | 10% |
| Eligibility quality | 5% |

Weights must total exactly 100%.

## Evidence quality

Evidence quality is calculated from the average weight of the evidence
records attached to DecisionInput.

Evidence weights use a zero-to-one scale and are converted to a
zero-to-one-hundred component score.

## Evidence consistency

Evidence consistency is derived from:

`100 - evidence_conflict_score`

The conflict score is supplied through DecisionInput metadata and must be
between zero and one hundred.

## Eligibility quality

Default eligibility component values are:

| Eligibility status | Quality score |
|---|---:|
| Eligible | 100 |
| Conditionally eligible | 70 |
| Insufficient data | 35 |
| Ineligible | 20 |

## Explicit confidence adjustments

The engine supports adjustments for:

- conditional eligibility;
- partially stale evidence;
- limited evidence quantity;
- forecast-model disagreement;
- unsupported assumptions;
- unstable market regime.

Adjustments are stored separately from weighted components.

## Confidence bands

| Final confidence | Band |
|---|---|
| 0.85–1.00 | Very high |
| 0.70–0.849999 | High |
| 0.55–0.699999 | Moderate |
| 0.40–0.549999 | Low |
| 0.00–0.399999 | Very low |

## Metadata inputs

Optional zero-to-one-hundred metadata inputs include:

- evidence_conflict_score;
- forecast_model_disagreement;
- unsupported_assumption_score;
- regime_instability_score.

Invalid, nonnumeric, nonfinite, or out-of-range metadata is rejected.

## ConfidenceResult

The output retains:

- raw confidence;
- total adjustment score;
- final confidence;
- confidence band;
- weighted component scores;
- explicit adjustments;
- human-readable reasons;
- confidence version.

## Scope boundary

Phase 5.1.5 calculates recommendation confidence.

It does not:

- change the classified action;
- calculate capital allocation;
- evaluate execution constraints;
- construct the final DecisionResult.

Those responsibilities remain in later Decision Engine components.
