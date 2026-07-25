# Phase 8.9.9.1 — Dependency Inventory and Migration Contract

## Objective

Replace informal retirement assumptions with a machine-readable contract that identifies every capability still required for a standalone-free Metals production cycle.

## Current finding

The certified UIP Metals cycle still accepts an external `metals_root` and reads the standalone DuckDB and export surfaces. GitHub-hosted runners cannot access the local Windows path. Retirement is therefore blocked until UIP owns persistence, model execution, package generation, readiness, and the complete scheduled cycle.

## Contract

`config/metals/runtime_migration_contract.json` records:

- the legacy source responsibility;
- the exact UIP target;
- whether the capability is required;
- migration state;
- GitHub-hosted compatibility.

Allowed states are `IMPLEMENTED`, `PLANNED`, `BLOCKED`, and `RETIRED`.

## Validation rules

The validator fails closed when:

- an implemented target is absent;
- a required capability is blocked;
- a completed target still points outside UIP;
- a migration state is invalid.

It returns `INCOMPLETE` while required capabilities remain planned. It returns `PASS` only when all required capabilities are implemented or retired and GitHub-hosted compatible.

## Current migration boundary

Already UIP-native:

- provider checks;
- daily vehicle collection;
- vehicle metadata;
- daily overlay and divergence;
- methodology registry;
- outcome tracking;
- risk-aware constraints;
- canonical Metals configuration.

Still required:

- PostgreSQL-backed native observation persistence;
- UIP-native forecasting and decision execution;
- package generation without external `metals_root`;
- standalone-free readiness;
- complete GitHub Actions Metals cycle.

## Commands

```powershell
python -m pytest tests\production\test_metals_runtime_migration.py -q
python scripts\check_metals_runtime_migration.py
python scripts\check_metals_runtime_migration.py --strict
```

The current committed contract is expected to return `INCOMPLETE`; strict mode must return exit code `1`. This is correct until the remaining migration targets are implemented.
