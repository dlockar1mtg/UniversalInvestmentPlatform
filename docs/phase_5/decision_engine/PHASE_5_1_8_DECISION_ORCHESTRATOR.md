# Phase 5.1.8 — Universal Decision Orchestrator

## Objective

Coordinate the complete single-opportunity decision workflow and produce
a final DecisionResult plus all intermediate decision artifacts.

## Pipeline

The orchestrator invokes:

1. UniversalEligibilityEngine
2. UniversalDecisionScoringEngine
3. UniversalActionClassificationEngine
4. UniversalConfidenceAggregationEngine
5. UniversalConstraintEngine
6. UniversalAllocationEngine
7. UniversalDecisionExplanationEngine

## Safe short-circuit behavior

Eligible and conditionally eligible opportunities proceed through normal
scoring.

Ineligible and insufficient-data opportunities receive a transparent
zero DecisionScore with scoring version:

`5.1.8-short-circuit`

They still proceed through classification, confidence, constraints,
allocation, and explanation so the final outcome remains complete and
auditable.

## Decision identifiers

Decision identifiers are reproducibly generated from:

- asset identifier;
- asset class;
- time horizon;
- portfolio identifier;
- generation timestamp;
- policy identifier;
- policy version.

A caller may supply an explicit decision identifier.

## Decision lifecycle

New orchestrated decisions receive:

- DecisionStatus.EVALUATED;
- a timezone-aware generation timestamp;
- an expiration timestamp;
- policy and component version metadata.

The default expiration window is twenty-four hours.

## Final DecisionResult

The final DecisionResult includes:

- decision identifier;
- asset identifier and class;
- action;
- lifecycle status;
- eligibility status;
- DecisionScore;
- final confidence;
- maximum permitted allocation;
- recommended allocation;
- reasons;
- evidence;
- policy violations;
- policy identifiers and versions;
- generation and expiration timestamps;
- orchestration metadata.

## DecisionOrchestrationResult

The orchestration wrapper preserves:

- final DecisionResult;
- EligibilityResult;
- ActionClassificationResult;
- ConfidenceResult;
- ConstraintEvaluationResult;
- AllocationResult;
- DecisionExplanation;
- engine version.

## Metadata

Optional metadata includes:

- component versions;
- explanation summary;
- intermediate result values;
- audit facts;
- original DecisionInput metadata.

## Separation of responsibilities

The orchestrator coordinates components but does not duplicate their
business logic.

It does not:

- calculate eligibility rules directly;
- calculate weighted scoring components;
- choose action thresholds;
- calculate confidence weights;
- calculate portfolio constraints;
- calculate allocation multipliers;
- invent explanation content.

## Scope boundary

Phase 5.1.8 creates a complete in-memory decision result.

Stable JSON, CSV, summary, and audit serialization are implemented in
Phase 5.1.9.
