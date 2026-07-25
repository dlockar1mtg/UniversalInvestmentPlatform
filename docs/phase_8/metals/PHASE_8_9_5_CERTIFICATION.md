# Phase 8.9.5 — Industrial Metals Vehicle Coverage Certification

## Certification decision

**PASS — Phase 8.9.5 is approved for merge.**

Certification date: 2026-07-25

Branch: `phase-8.9.5-metals-industrial-vehicle-coverage`

## Certified scope

Phase 8.9.5 adds explicit industrial-metal vehicle coverage for:

- aluminum;
- zinc;
- nickel;
- tin.

The implementation records benchmark mappings, candidate vehicles, candidate structure, approved-vehicle state, research-only state, selection eligibility, validation status, and decision rationale.

## Fail-closed decision model

The certified result intentionally allows complete coverage with zero eligible vehicles.

A metal remains blocked from platform selection unless a currently listed, liquid, approved vehicle is supported by sufficient evidence. Historical or legacy ETNs may be retained as research candidates but cannot become selectable solely because they once existed.

## Validation record

- Focused Phase 8.9.5 tests: 5 passed
- Production tests: 115 passed
- Full-platform regression tests: 1,130 passed
- Existing nonblocking warning: one FastAPI/Starlette test-client deprecation warning
- Non-strict publication: PASS
- Strict publication: PASS
- Strict exit code: 0
- Git working tree: clean

## Certified operational evidence

- Metal count: 4
- Eligible metal count: 0
- Research-only count: 4
- Blocked metal count: 4
- Fail-closed: true
- Overall status: PASS

## Certified metal decisions

- Aluminum: `RESEARCH_ONLY`; legacy candidate `JJU`; benchmark `ALI=F`; not selection eligible.
- Zinc: `RESEARCH_ONLY`; no approved U.S.-accessible single-metal vehicle identified; not selection eligible.
- Nickel: `RESEARCH_ONLY`; legacy candidate `JJN`; not selection eligible.
- Tin: `RESEARCH_ONLY`; legacy candidate `JJT`; not selection eligible.

Each row passed structural and eligibility validation.

## Published outputs

The publisher generated:

- `industrial_vehicle_coverage_summary.json`;
- `industrial_vehicle_coverage.json`;
- `industrial_vehicle_coverage.csv`.

Runtime outputs remain under `data/operations/metals/industrial_vehicle_coverage` and are not committed.

## Certification conclusion

Phase 8.9.5 satisfies its intended purpose. The platform now distinguishes research coverage from investable coverage and prevents legacy, inactive, unverified, or illiquid industrial-metal products from entering portfolio selection.

Future updates may promote a metal to an approved state only after current listing, structure, cost, spread, volume, and accessibility evidence is collected and validated.
