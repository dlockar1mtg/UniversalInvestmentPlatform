# Phase 5.1.7 — Universal Decision Explanation Engine

## Objective

Convert structured decision artifacts into executive, analytical, and
audit-ready explanations without inventing unsupported reasoning.

## Inputs

The explanation engine consumes:

- DecisionInput;
- EligibilityResult;
- DecisionScore;
- ActionClassificationResult;
- ConfidenceResult;
- ConstraintEvaluationResult;
- AllocationResult.

All artifacts must reference the same asset.

Classification and allocation actions must match.

Classification eligibility must match the EligibilityResult status.

## Explanation layers

### Executive explanation

The headline and executive summary provide:

- asset identifier;
- action;
- decision score;
- confidence;
- maximum allocation;
- recommended allocation;
- constraint status.

### Analytical explanation

The analytical layer contains:

- strongest positive scoring factors;
- explicit scoring penalties;
- confidence adjustments;
- failed eligibility checks;
- constraint warnings;
- allocation warnings.

### Audit explanation

Audit facts retain:

- asset and portfolio identifiers;
- eligibility status;
- policy version;
- score values;
- scoring version;
- action;
- classification version;
- confidence values;
- confidence version;
- constraint status;
- binding constraint;
- constraint version;
- allocation values;
- allocation version;
- evidence count.

## No invented reasoning

The engine may only explain information contained in the supplied
decision artifacts.

It does not infer external causes, future events, market narratives, or
investment theses that are absent from structured inputs.

## Positive factors

Positive factors are selected from:

- weighted DecisionScore components;
- final recommendation confidence.

Factors are ranked by their numeric contribution.

## Negative factors

Negative factors are selected from:

- scoring penalties;
- confidence adjustments;
- failed eligibility checks;
- blocked constraints.

## Warnings

Warnings may be generated for:

- conditional eligibility;
- low confidence;
- warning-level constraints;
- blocked constraints;
- zero recommended allocation.

## Evidence references

Evidence references use DecisionEvidence identifiers rather than copying
or rewriting the evidence content.

## ExplanationProfile

The explanation profile controls:

- maximum positive factors;
- maximum negative factors;
- maximum warnings;
- maximum evidence references;
- whether audit facts are included.

## Scope boundary

Phase 5.1.7 explains completed structured decision artifacts.

It does not:

- calculate eligibility;
- calculate scores;
- classify actions;
- calculate confidence;
- evaluate constraints;
- calculate allocations;
- construct the final DecisionResult.

Those responsibilities remain in their respective components.
