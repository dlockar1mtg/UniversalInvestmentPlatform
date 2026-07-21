# Phase 8.4 — Metals Vehicle Intelligence and Constraint Certification

## Certification decision

**PASS — deterministic Metals vehicle selection and concentration controls are approved for production integration.**

Evaluation date: 2026-07-21

Branch: `phase-8-metals-production-hardening`

## Implemented controls

- Minimum vehicle score with deterministic fallback
- Maximum candidates per asset
- Minimum direct-exposure share
- Maximum miner and thematic-equity share
- Maximum single-vehicle share
- Forced admission of a direct vehicle when required
- Admission of additional candidates when necessary to make a concentration cap feasible
- Explicit rejection of infeasible constraints
- Exact 100 percent allocation using decimal arithmetic
- Stable score and ticker ordering
- Registry ownership and enablement validation
- Unknown, duplicate, cross-asset, and invalid-score rejection

## Certified representative allocations

| Asset | Certified outcome |
|---|---|
| Gold | GLD 44.117647%, IAU 29.411765%, SGOL 26.470588% |
| Silver | SLV 59.090909%, SIVR 40.909091% |
| Copper | COPX 60%, CPER 40% |
| Uranium | URA 60%, URNM 40% |
| Platinum | PPLT 100% |
| Tactical reserve | BIL 100% |

Copper preserves the legacy structural intent: at least 40 percent direct exposure through CPER
and no more than 60 percent miner exposure through COPX.

Gold, silver, and uranium diversification limits prevent one eligible vehicle from exceeding
60 percent. Platinum and the tactical reserve permit 100 percent allocations because only one
registered implementation vehicle exists for each.

## Reliability assessment

The implementation is pure deterministic logic. It does not depend on DuckDB, pandas, NumPy,
yfinance, mutable root paths, or network access.

Constraints are stored separately from code in
`config/metals/vehicle_constraints.json` and are validated against the canonical Phase 8.3
registry before use.

The selector fails closed when:

- a direct-exposure requirement has no direct vehicle;
- combined concentration limits are mathematically infeasible;
- a candidate is unknown, duplicated, disabled, or assigned to another asset;
- a score is non-finite or outside 0 through 100;
- configuration references an unknown asset.

## Automated validation

- Focused registry and constraint tests: 16 passed
- Production test suite: 68 passed
- Full platform regression suite: 1,060 passed
- Operator constraint health check: PASS
- Non-blocking warnings: one existing FastAPI/Starlette deprecation warning
- Repository status: clean
- Blocking defects: none

## Completion decision

Phase 8.4 is complete. The reusable legacy Metals vehicle constraints have been replaced by a
validated universal implementation without importing the legacy runtime.

Proceed to **Phase 8.5 — Metals Native Export and Persistence Independence**.
