# Phase 8.9.5 — Industrial Metals Vehicle Coverage

## Objective

Add explicit platform coverage decisions for aluminum, zinc, nickel, and tin without treating a historical ticker or research benchmark as an approved investment vehicle.

## Policy

Industrial-metal coverage is fail-closed. A vehicle may become selectable only when all required evidence is present:

- current listing evidence;
- current market metadata;
- acceptable liquidity;
- acceptable spread;
- approved legal structure.

The absence of an approved vehicle does not remove the metal from research coverage. It prevents the platform from producing a selection recommendation that cannot be executed reliably.

## Current decisions

The initial 2026-07-25 decision set classifies aluminum, zinc, nickel, and tin as `RESEARCH_ONLY`.

Historical Barclays iPath ETNs were identified for aluminum, nickel, and tin. They remain candidates for research and historical mapping, not approved platform vehicles. Aluminum and broad industrial-metals products are independently classified as inactive, and current issuer/listing evidence was not approved for any of the four required metals.

Zinc currently has no approved U.S.-accessible single-metal candidate in the registry.

## Coverage statuses

- `DIRECTLY_INVESTABLE`
- `FUND_ONLY`
- `FUTURES_ONLY`
- `RESEARCH_ONLY`
- `NO_APPROVED_VEHICLE`

`RESEARCH_ONLY` and `NO_APPROVED_VEHICLE` records can never be selection eligible.

## Configuration

The canonical decisions are stored in:

```text
config/metals/industrial_vehicle_coverage.json
```

The configuration contains:

- required-metal policy;
- benchmark symbol when available;
- candidate ticker history;
- structure and exposure classification;
- decision rationale;
- source-reference labels;
- selection eligibility.

## Publication

Run:

```powershell
python scripts\publish_metals_industrial_vehicle_coverage.py --strict
```

Outputs are written to:

```text
data/operations/metals/industrial_vehicle_coverage/
```

Generated files:

- `industrial_vehicle_coverage.json`
- `industrial_vehicle_coverage.csv`
- `industrial_vehicle_coverage_summary.json`

Runtime outputs are ignored by Git.

## Validation behavior

Validation fails when:

- any required metal is missing;
- an unexpected metal is added;
- identifiers are duplicated;
- fail-closed policy is disabled;
- a coverage status is invalid;
- a decision rationale is missing;
- a research-only or no-approved-vehicle record is marked selectable.

A valid coverage matrix may pass with zero eligible metals. This is intentional: coverage completeness and investment eligibility are separate concepts.

## Definition of done

Phase 8.9.5 is complete when:

1. all four required metals are represented;
2. every record has an explicit coverage decision;
3. no unverified vehicle is selection eligible;
4. focused tests pass;
5. production tests pass;
6. the full regression suite passes;
7. strict publication returns zero;
8. published outputs show four covered and four blocked metals until approved vehicle evidence is added.
