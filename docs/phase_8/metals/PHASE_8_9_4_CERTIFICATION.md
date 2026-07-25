# Phase 8.9.4 — Metals Vehicle Metadata Certification

## Certification decision

**PASS — Phase 8.9.4 is approved for merge.**

Certification date: 2026-07-25

Branch: `phase-8.9.4-metals-vehicle-metadata`

## Certified scope

Phase 8.9.4 establishes canonical structural and dated market metadata for every registered Metals investment vehicle.

The certified implementation provides:

- structural metadata for all 11 canonical vehicles;
- issuer, legal structure, exposure type, exposure share, concentration, tax structure, and investability classification;
- dated expense-ratio, assets-under-management, average-volume, and bid/ask-spread observations;
- source name and source URL provenance;
- completeness and freshness classification;
- strict fail-closed validation;
- dashboard-ready JSON and CSV outputs;
- vehicle selection eligibility based on complete, current evidence;
- registry coverage validation;
- collection and publication runners;
- issuer spread fallback for BIL when market bid/ask fields are unavailable.

## Validation record

- Focused Phase 8.9.4 tests: 8 passed
- Production tests: 105 passed
- Full-platform regression tests: 1,120 passed
- Existing nonblocking warning: one FastAPI/Starlette test-client deprecation warning
- Collection status: COMPLETE
- Strict publication status: PASS
- Strict publication exit code: 0
- Incomplete metadata rows: 0
- Registered vehicles: 11
- Complete vehicles: 11
- Current vehicles: 11
- Eligible vehicles: 11

## Certified dated metadata

Metadata effective date: `2026-07-25`

The certified dataset contains all required fields for:

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

BIL's market provider did not expose a usable bid/ask pair during collection. The collector therefore used the issuer-published 30-day median bid/ask spread fallback of `0.01%`, retained the State Street source URL, and recorded the fallback in source provenance.

## Failure behavior verified

Before live metadata collection, all 11 vehicles were classified as incomplete and strict mode exited with code 1.

After the first collection, BIL remained incomplete because spread evidence was absent, while the other 10 vehicles passed. Strict mode continued to exit with code 1.

After adding the issuer fallback, all 11 vehicles became complete, current, and eligible. Strict mode exited with code 0.

This sequence demonstrates that the implementation does not silently certify blank market data and only advances a vehicle when every required field has valid dated evidence.

## Certification conclusion

Phase 8.9.4 satisfies its intended purpose. The Metals platform now has a complete, dated, provenance-aware vehicle metadata layer suitable for selection logic, operational review, dashboards, and later market-overlay work.
