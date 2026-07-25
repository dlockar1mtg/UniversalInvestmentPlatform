# Phase 8.9.6 Certification — Metals Out-of-Sample Outcome Tracking

## Certification status

**PASS**

Phase 8.9.6 is certified as a production-ready outcome-evaluation adapter for Metals forecasts and recommendations.

## Scope certified

The implementation evaluates matured forecast outcomes and publishes machine-readable evidence for:

- forecast absolute error and RMSE;
- directional accuracy;
- probability calibration error;
- recommendation hit rate;
- post-signal return;
- benchmark-relative excess return;
- regime-level performance;
- estimated vehicle slippage;
- net return after slippage;
- portfolio contribution.

## Validation evidence

Validation date: 2026-07-25

### Automated tests

- Focused Phase 8.9.6 tests: **5 passed**
- Production test suite: **120 passed**
- Full platform regression suite: **1,135 passed**
- Existing nonblocking FastAPI/Starlette test-client warning remains.

### Deterministic validation sample

The committed validation sample contains three synthetic, deterministic matured outcomes used only to certify calculations and output behavior.

Certified result:

- Status: `PASS`
- Outcome count: `3`
- Directional accuracy: `100.0%`
- Recommendation hit rate: `100.0%`
- Mean absolute error: `1.5%`
- RMSE: `1.658312%`
- Mean calibration error: `0.316667`
- Mean post-signal return: `1.666667%`
- Mean excess return: `0.366667%`
- Mean slippage: `0.093333%`
- Total portfolio contribution: `0.3483%`
- Strict exit code: `0`

These metrics certify deterministic computation only and are not represented as historical production performance.

### Fail-closed live behavior

Running strict mode without a populated live matured-outcome input produced:

- Status: `NO_OUTCOMES`
- Outcome count: `0`
- Exit code: `1`

This confirms that an empty live outcome history cannot be mistaken for certified performance.

## Operational outputs

The publisher writes:

- `metals_outcomes.json`
- `metals_outcomes.csv`
- `metals_outcome_summary.json`
- `metals_regime_performance.json`

under:

`data/operations/metals/outcome_tracking/`

## Certification decision

Phase 8.9.6 meets its intended definition of done for outcome contracts, deterministic evaluation, regime and vehicle attribution, operational publication, strict validation, regression safety, and fail-closed handling of missing live outcomes.

Live longitudinal performance evidence will accumulate only after actual Metals forecasts mature and are supplied through the production input path.
