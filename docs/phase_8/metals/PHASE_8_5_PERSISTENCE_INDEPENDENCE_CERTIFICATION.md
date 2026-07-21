# Phase 8.5 — Metals Native Export and Persistence Independence Certification

## Certification decision

**PASS — the Metals universal adapter is certified to operate without the legacy DuckDB or legacy Python runtime.**

Evaluation date: 2026-07-21

Branch: `phase-8-metals-production-hardening`

## Implemented boundary

Five legacy-only database views are exported once into a verified file handoff:

| Surface | Rows |
|---|---:|
| vehicle recommendations | 11 |
| recommendation history | 10 |
| portfolio risk metrics | 1 |
| risk contributions | 10 |
| portfolio positions | 6 |

Total bridge records: 38.

Each surface is recorded in `metals_bridge_export_manifest.json` with its source view, row
count, and SHA-256 checksum. The manifest is published last, after all staged CSVs are complete.

## Runtime independence

The normal adapter path now reads the verified CSV handoff. It fails closed when:

- the manifest is absent or malformed;
- a required surface is undeclared or missing;
- a checksum differs;
- a row count differs;
- a required surface is empty.

Direct DuckDB reads are disabled by default. They require the explicit
`--allow-legacy-database-fallback` flag and exist only as a transitional recovery mechanism.

## Independence proof

The universal package was built successfully twice:

1. From the live standalone Metals project.
2. From a temporary handoff directory containing only `data/exports`.

The second source contained no DuckDB database and no legacy Metals runtime.

Certified packages:

- Live-root package: `metals-20260721T112728Z-7d3fe893`
- Export-only package: `metals-20260721T112735Z-7271415e`

Both results: `METALS UNIVERSAL EXPORT: PASS`.

## Defect closure

Initial validation exposed a missing export-root argument in the risk bridge call. The defect was
corrected, and a regression test now executes that boundary directly. The complete independence
proof then passed.

## Automated validation

- Native-surface integration tests: 6 passed
- Production test suite: 68 passed
- Full platform regression suite: 1,066 passed
- Non-blocking warnings: one existing FastAPI/Starlette deprecation warning
- Repository status: clean
- Blocking defects: none

## Completion decision

Phase 8.5 is complete. The universal platform can retain and process the Metals integration
package after the standalone database and application are retired.

Proceed to **Phase 8.6 — Metals Historical Parity and Model Validation**.
