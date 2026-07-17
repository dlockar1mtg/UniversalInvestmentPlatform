# Phase 5.1.4 — Universal Action Classification Engine

## Objective

Convert an eligibility outcome and final decision score into a
standardized investment action.

## Inputs

The engine consumes:

- DecisionInput;
- DecisionScore;
- EligibilityResult;
- DecisionPolicy.

## Position detection

An opportunity is treated as an existing position when either:

- current position value is greater than zero; or
- current asset weight is greater than zero.

This distinction changes the meaning of neutral and weak scores.

## Default action thresholds

| Final score | New opportunity | Existing position |
|---|---|---|
| 85–100 | STRONG_BUY | STRONG_BUY |
| 72–84.999 | BUY | BUY |
| 62–71.999 | ACCUMULATE | ACCUMULATE |
| 50–61.999 | WAIT | HOLD |
| 38–49.999 | AVOID | REDUCE |
| 0–37.999 | AVOID | SELL |

The sell threshold remains part of policy configuration and separates
ordinary reduction territory from stronger exit territory for existing
positions.

## Eligibility overrides

Eligibility is evaluated before score thresholds.

### Ineligible

Always produces INELIGIBLE, regardless of score.

### Insufficient Data

Always produces INSUFFICIENT_DATA, regardless of score.

### Conditionally Eligible

May proceed to classification, but positive actions are capped at
ACCUMULATE.

This prevents unresolved data-quality or eligibility concerns from
producing BUY or STRONG_BUY recommendations.

## Ownership-sensitive actions

HOLD, REDUCE, and SELL require an existing position.

For a new opportunity, equivalent score ranges produce WAIT or AVOID.

## Explainability

Every classification result contains:

- selected action;
- eligibility status;
- final score;
- position-existence flag;
- human-readable reasons;
- classification version.

## Scope boundary

Phase 5.1.4 classifies actions.

It does not yet:

- calculate final recommendation confidence;
- calculate maximum deployable allocation;
- evaluate additional execution constraints;
- assemble the complete DecisionResult.
