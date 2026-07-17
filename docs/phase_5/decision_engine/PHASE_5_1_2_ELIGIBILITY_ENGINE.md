# Phase 5.1.2 — Universal Eligibility and Data Quality Engine

## Objective

Determine whether an investment opportunity has sufficient intelligence,
evidence, liquidity, capital availability, and portfolio capacity to
proceed into universal decision scoring.

## Eligibility outcomes

### Eligible

The opportunity passes all active rules and may proceed to scoring.

### Conditionally Eligible

One or more noncritical rules fall slightly below policy requirements.
The opportunity may proceed, but the condition must remain visible in
the final recommendation.

### Insufficient Data

The opportunity lacks enough reliable or current information to support
a responsible decision.

### Ineligible

The opportunity violates a hard portfolio, capital, concentration, or
liquidity rule.

## Evaluated categories

- Data quality
- Forecast confidence
- Historical reliability
- Liquidity quality
- Evidence quantity
- Evidence freshness
- Available capital
- Current asset concentration
- Current asset-class concentration

## Status precedence

When multiple failures occur, the engine applies this precedence:

1. Ineligible
2. Insufficient Data
3. Conditionally Eligible
4. Eligible

A hard portfolio or investability violation therefore cannot be hidden
by a lower-severity data-quality warning.

## Conditional tolerance

A configurable shortfall tolerance allows a score that is slightly below
a minimum to receive a conditional result rather than being immediately
rejected.

The default tolerance is ten score points.

## Evidence freshness

Evidence is evaluated relative to the portfolio context timestamp.

The default evidence freshness window is forty-five days.

- All evidence fresh: pass
- Some evidence stale: conditionally eligible
- All evidence stale: insufficient data

## Scope boundary

Phase 5.1.2 determines whether an opportunity may proceed to scoring.

It does not yet:

- calculate a weighted decision score;
- classify buy, hold, reduce, or sell actions;
- calculate recommendation confidence;
- calculate deployable allocation;
- generate a complete DecisionResult.
