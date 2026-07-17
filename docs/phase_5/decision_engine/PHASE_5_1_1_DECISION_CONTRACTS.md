# Phase 5.1.1 — Decision Contracts and Domain Models

## Objective

Establish the universal vocabulary and validated data structures used by
all later Phase 5.1 components.

## Implemented contracts

### DecisionAction

Defines the standard action vocabulary:

- strong_buy
- buy
- accumulate
- hold
- wait
- reduce
- sell
- avoid
- ineligible
- insufficient_data

### DecisionStatus

Tracks the lifecycle of a decision:

- draft
- evaluated
- approved
- rejected
- superseded
- expired
- certified

### EligibilityStatus

Records the pre-classification eligibility outcome:

- eligible
- conditionally_eligible
- ineligible
- insufficient_data

### DecisionEvidence

Provides a traceable evidence record with:

- evidence identifier;
- category;
- source;
- description;
- value;
- weight;
- observation timestamp;
- metadata.

### DecisionContext

Provides portfolio and capital context, including:

- portfolio value;
- available capital;
- current position value;
- current asset exposure;
- current asset-class exposure;
- optional target weights.

### DecisionInput

Standardizes the intelligence supplied to the decision engine.

All score-like input fields use a zero-to-one-hundred scale.

### DecisionPolicy

Defines configurable eligibility, allocation, and action thresholds.

### DecisionScore

Stores the transparent component, penalty, and final score breakdown.

### DecisionResult

Provides the complete auditable output of a decision evaluation.

## Validation conventions

- Percentage scores use the range 0 through 100.
- Portfolio weights use the range 0 through 1.
- Final confidence uses the range 0 through 1.
- Monetary values use Decimal.
- Timestamps must be timezone aware.
- Decision and policy identifiers cannot be blank.
- Expiration must occur after generation.
- Action thresholds must be ordered from highest to lowest.

## Scope boundary

Phase 5.1.1 defines and validates decision objects.

It does not yet:

- calculate eligibility;
- calculate decision scores;
- classify actions;
- calculate maximum allocations;
- aggregate confidence;
- generate explanations.

Those capabilities are implemented in later Phase 5.1 subphases.
