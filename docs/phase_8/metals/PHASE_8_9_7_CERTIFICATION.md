# Phase 8.9.7 Certification — Risk-Aware Vehicle Constraints

## Result

**PASS**

Phase 8.9.7 is certified as complete based on deterministic validation, strict fail-closed behavior, and full regression coverage.

## Scope certified

The implementation adds a Metals-specific pre-allocation risk gate that preserves the existing purchase-rounding engine while adding deterministic, explainable vehicle constraints.

Certified risk dimensions:

- liquidity;
- bid/ask spread;
- expense ratio;
- futures roll drag;
- miner beta;
- company concentration;
- geographic concentration;
- currency exposure;
- tax structure;
- portfolio overlap;
- portfolio factor exposure;
- metadata freshness;
- explicit vehicle approval state.

Certified decision states:

- `ELIGIBLE`;
- `CAPPED`;
- `BLOCKED`.

## Validation results

### Focused Phase 8.9.7 tests

- Result: **6 passed**
- Warning: one existing nonblocking FastAPI/Starlette test-client deprecation warning

### Production test suite

- Result: **126 passed**
- Warning: one existing nonblocking FastAPI/Starlette test-client deprecation warning

### Full platform regression suite

- Result: **1,141 passed**
- Warning: one existing nonblocking FastAPI/Starlette test-client deprecation warning

## Deterministic validation sample

Strict publication using the committed validation sample returned:

- Status: `PASS`
- Vehicle count: 4
- Eligible: 1
- Capped: 2
- Blocked: 1
- Strict exit code: 0

Certified sample decisions:

- IAU: `ELIGIBLE`, maximum allocation 10.0%, reason `WITHIN_POLICY`;
- SLV: `CAPPED`, maximum allocation 2.0%, reason `PORTFOLIO_OVERLAP`;
- COPX: `CAPPED`, maximum allocation 2.5%, reasons include high miner beta, country concentration, currency exposure, and factor exposure;
- JJU: `BLOCKED`, maximum allocation 0.0%, reasons include unapproved vehicle, stale metadata, blocked tax structure, low liquidity, wide spread, and high roll drag.

The committed validation sample is synthetic and deterministic. It certifies rule behavior and output generation only; it is not a production portfolio recommendation.

## Fail-closed live behavior

With no populated live vehicle-risk input file:

- Status: `NO_VEHICLES`
- Vehicle count: 0
- Strict exit code: 1

This confirms that missing live risk evidence cannot be mistaken for an approved allocation state.

## Operational outputs

The publisher writes dashboard-ready JSON and CSV output under:

`data/operations/metals/risk_aware_constraints`

Runtime outputs remain outside tracked source control.

## Repository state

- Branch: `phase-8.9.7-metals-risk-aware-constraints`
- Working tree: clean after validation
- Required runtime outputs: generated successfully
- Regression failures: none

## Certification statement

Phase 8.9.7 is certified because it preserves deterministic purchase execution, adds an explainable risk-aware pre-allocation gate, enforces hard blocks and allocation caps, publishes machine-readable decisions, fails closed when live evidence is absent, and passes all focused, production, and platform regression tests.
