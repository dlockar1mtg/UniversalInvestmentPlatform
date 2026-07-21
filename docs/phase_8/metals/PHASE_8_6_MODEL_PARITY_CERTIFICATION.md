# Phase 8.6 — Metals Historical Parity and Model Validation Certification

## Certification decision

**PASS — Metals v8 model evidence and universal transformation parity are certified.**

Evaluation date: 2026-07-21

Branch: `phase-8-metals-production-hardening`

Certified package: `metals-20260721T114844Z-b6d15655`

## Certified evidence

| Check | Records | Result |
|---|---:|---|
| Forecast keys | 16 | PASS |
| Forecast model components | 64 | PASS |
| Learned regime probabilities | 12 | PASS |
| Uncertainty-adjusted views | 32 | PASS |
| Forecast transformations | 16 | PASS |
| Opportunity recommendation identities | 2 | PASS |
| Portfolio positions | 6 | PASS |
| Portfolio and contribution risk rows | 11 | PASS |
| Supporting native evidence files | 7 | PASS |

## Model validation controls

- Forecast keys are unique by metal and horizon.
- Every forecast has complete multi-model component coverage.
- Each forecast has at least two model components.
- Model weights sum to exactly one within tolerance.
- All evidence belongs to the certified forecast run.
- Regime probabilities are numeric and bounded between zero and one.
- Regime probabilities sum to one for every metal.
- Regime and forecast metal universes match.
- Uncertainty-adjusted views have no orphan forecast keys.
- Adjusted returns reconcile to raw return less uncertainty and downside penalties.

## Transformation parity controls

The universal package preserves:

- canonical commodity and vehicle identifiers;
- forecast horizon keys;
- expected total returns;
- positive-return probabilities;
- forecast confidence;
- recommendation asset identity;
- position quantities and market values;
- portfolio and component risk coverage;
- all seven supporting model and audit evidence files.

## Defects discovered and closed

### Forecast contract loss

Native `expected_return` was originally emitted under a name not present in the universal
forecast contract. Contract projection therefore produced a blank optional value.

The adapter now maps:

- `expected_return` to `expected_total_return`;
- one minus downside probability to `probability_positive_return`;
- model agreement to `forecast_confidence`;
- the source model version to `metals-v8.1`.

### Position contract and identity drift

Legacy `ticker` and `shares` fields were not canonical universal position columns, and fallback
vehicle identifiers were lowercased.

The adapter now maps native positions into quantity, unit value, position value, cost basis, and
source platform fields. Vehicle identifiers use the registry-owned uppercase form such as
`metals:vehicle:GLD`.

Both corrections have regression tests.

## Automated validation

- Focused native-surface and model-parity tests: 13 passed
- Production test suite: 68 passed
- Full platform regression suite: 1,073 passed
- Semantic parity checker: PASS
- Non-blocking warnings: one existing FastAPI/Starlette deprecation warning
- Repository status: clean
- Blocking defects: none

## Completion decision

Phase 8.6 is complete. The certified package preserves the live Metals v8 decision evidence and
all universal contract values selected for first-class integration.

Proceed to **Phase 8.7 — Metals Production Operations and Dashboard Readiness**.
