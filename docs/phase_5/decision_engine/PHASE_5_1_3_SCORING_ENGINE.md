# Phase 5.1.3 — Universal Decision Scoring Engine

## Objective

Calculate a transparent universal opportunity score for investments that
are permitted to proceed beyond eligibility evaluation.

## Scoring components

The default balanced profile uses:

| Component | Weight |
|---|---:|
| Forecast strength | 20% |
| Forecast confidence | 15% |
| Historical reliability | 15% |
| Risk-adjusted opportunity | 15% |
| Market-regime alignment | 10% |
| Diversification fit | 10% |
| Liquidity quality | 5% |
| Valuation attractiveness | 10% |

The weights must total exactly 100%.

## Base score

Each zero-to-one-hundred input is multiplied by its configured weight.

The weighted values are retained individually in
`DecisionScore.component_scores`, making the calculation auditable.

## Explicit penalties

The engine supports separate penalties for:

- imperfect data quality;
- conditional eligibility;
- concentration near the maximum asset limit;
- concentration near the maximum asset-class limit;
- partially stale evidence;
- conflicting evidence.

Penalties are not hidden inside component scores. They are stored in
`DecisionScore.penalty_components`.

## Data-quality penalty

The default maximum data-quality penalty is eight points.

The penalty scales proportionally with the distance below perfect data
quality.

## Concentration penalties

Concentration penalties begin when exposure exceeds a configurable
percentage of the active policy limit.

The default warning point is 75% of the maximum permitted exposure.

An opportunity already above the policy maximum is ineligible and never
reaches scoring.

## Evidence conflict

Asset adapters may provide an `evidence_conflict_score` in
`DecisionInput.metadata`.

This score must be numeric and between zero and one hundred.

The default maximum evidence-conflict penalty is eight points.

## Eligibility requirement

Only these statuses may proceed:

- eligible;
- conditionally eligible.

These statuses are rejected:

- insufficient data;
- ineligible.

## Final score

The final score is:

Base score minus explicit penalties.

The result is constrained to the range zero through one hundred.

## Scope boundary

Phase 5.1.3 calculates the decision score.

It does not yet:

- classify the score as buy, hold, reduce, or sell;
- calculate final recommendation confidence;
- calculate deployable capital;
- generate the complete DecisionResult.
