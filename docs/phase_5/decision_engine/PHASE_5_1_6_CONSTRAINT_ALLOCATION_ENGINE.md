# Phase 5.1.6 — Universal Constraint and Allocation Engine

## Objective

Evaluate whether an investment recommendation may receive additional
capital and calculate a safe single-decision allocation.

## Constraint evaluation

The constraint engine evaluates:

- action permission;
- available capital;
- portfolio value;
- maximum asset weight;
- maximum asset-class weight;
- target asset allocation gap;
- target asset-class allocation gap;
- recommendation confidence;
- explicit policy prohibitions;
- liquidity allocation limits;
- minimum transaction requirements.

## Constraint statuses

### Passed

The rule permits normal allocation.

### Warning

Allocation may continue, but sizing should be reduced or reviewed.

### Blocked

The rule prevents additional allocation.

## Maximum permitted allocation

The maximum permitted allocation is the minimum monetary capacity across
all applicable constraints.

Potential binding limits include:

- available capital;
- remaining asset-level capacity;
- remaining asset-class capacity;
- target allocation gap;
- liquidity limit;
- hard policy prohibition.

## Allocation actions

Only capital-increasing actions may receive a positive allocation:

- STRONG_BUY;
- BUY;
- ACCUMULATE.

The following actions always receive zero additional allocation:

- HOLD;
- WAIT;
- REDUCE;
- SELL;
- AVOID;
- INELIGIBLE;
- INSUFFICIENT_DATA.

## Default action sizing

| Action | Multiplier |
|---|---:|
| STRONG_BUY | 1.00 |
| BUY | 0.75 |
| ACCUMULATE | 0.50 |
| Other actions | 0.00 |

## Confidence sizing

Final confidence is used as a sizing multiplier.

A configurable minimum confidence multiplier prevents extremely small
nonzero sizing when the action still permits allocation.

This does not override hard constraints.

## Conditional eligibility

Conditionally eligible decisions receive an additional allocation
multiplier.

The default multiplier is 0.50.

## Single-decision limit

A configurable maximum single-decision fraction limits how much of the
safe allocation capacity may be used by one recommendation.

Portfolio-wide competition between opportunities remains outside this
component.

## Metadata inputs

Optional DecisionInput metadata includes:

- allocation_prohibited;
- liquidity_allocation_limit;
- minimum_transaction_amount.

Invalid numeric metadata is rejected.

## AllocationResult

The final allocation result retains:

- requested allocation;
- maximum permitted allocation;
- recommended allocation;
- allocation percentage;
- binding constraint;
- sizing factors;
- human-readable reasons;
- allocation version.

## Scope boundary

Phase 5.1.6 calculates a safe allocation for one decision.

It does not distribute a monthly capital budget across multiple assets.
That responsibility belongs to the later portfolio-wide Capital
Allocation Engine.
