# Phase 8.3 — Metals Configuration and Asset Registry Certification

## Certification decision

**PASS — the canonical Metals asset and vehicle registry is approved for production integration.**

Evaluation date: 2026-07-20

Branch: `phase-8-metals-production-hardening`

## Certified registry

- Registry schema version: 1.0
- Registered assets: 10
- Registered commodities: 9
- Registered investment vehicles: 11
- Enabled investment vehicles: 11
- Adapter crosswalk: MATCH

Canonical commodity identifiers now use the `metals:commodity:<slug>` namespace across the
registry, certified adapter, and official-provider ingestion layer.

## Commodity universe

- aluminum
- copper
- gold
- nickel
- platinum
- silver
- tin
- uranium
- zinc

The registry also defines `metals:reserve:usd` for the tactical reserve represented by BIL.

## Vehicle universe

- BIL
- COPX
- CPER
- GLD
- IAU
- PPLT
- SGOL
- SIVR
- SLV
- URA
- URNM

Every vehicle has a stable vehicle identifier, canonical underlying asset, structural vehicle
type, allocation role, enablement state, and official product URL.

Mutable expense-ratio data is optional and must include an as-of date whenever populated. This
prevents an undated fee value from becoming permanent reference data.

## Integrity controls

- Unique asset identifiers, slugs, and symbols
- Unique vehicle identifiers and tickers
- Canonical identifier formats
- Uppercase symbols and tickers
- Vehicle-to-underlying referential integrity
- Benchmark-to-vehicle referential integrity
- HTTPS official-source URLs
- Valid strategic, tactical, and reserve roles
- Exact adapter-crosswalk compatibility
- Unknown asset and identity-drift rejection
- Provider output normalized to canonical asset identifiers

## Live provider validation

EIA and World Bank checks passed after the canonical-ID migration.

- EIA records: 1
- World Bank records: 8
- Provider status: PASS
- Retry attempts: 1 per provider

The deterministic fingerprints changed as expected because canonical asset identifiers are part
of the normalized batch content.

## Automated validation

- Focused registry and provider tests: 24 passed
- Production test suite: 60 passed
- Full platform regression suite: 1,052 passed
- Non-blocking warnings: one existing FastAPI/Starlette deprecation warning
- Repository status: clean
- Blocking defects: none

## Completion decision

Phase 8.3 is complete. Metals configuration now has one validated identity authority shared by
providers, vehicles, and the certified adapter.

Proceed to **Phase 8.4 — Metals Vehicle Intelligence and Constraint Integration**.
