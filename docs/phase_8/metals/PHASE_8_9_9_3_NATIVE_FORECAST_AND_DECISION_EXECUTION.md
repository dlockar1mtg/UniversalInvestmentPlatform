# Phase 8.9.9.3 — UIP-Native Forecast and Decision Execution

## Objective

Replace the standalone Metals forecast and recommendation runtime with a deterministic, versioned execution path that consumes only UIP-owned observations.

## Delivered

- `config/metals/model_methodology_registry.json`
  - versioned model identity;
  - explicit inputs, component weights, confidence policy, recommendation thresholds, bounds, and limitations;
  - declares that no external runtime is required.
- `foundation/production/metals_native_cycle.py`
  - groups UIP-native benchmark and vehicle observations;
  - computes bounded annualized trend evidence;
  - generates 12-, 36-, and 60-month forecasts;
  - publishes confidence, recommendations, and component evidence;
  - fails closed when model or benchmark evidence is missing.
- `scripts/run_metals_native_cycle.py`
  - reads the UIP-owned SQLite development store or PostgreSQL through `UIIP_DATABASE_URL`;
  - publishes JSON and CSV outputs under `data/operations/metals/native_cycle`;
  - supports strict nonzero exit behavior.
- `tests/production/test_metals_native_cycle.py`
  - validates horizon coverage, evidence, bounds, mathematics, failure behavior, publication, and the live methodology registry.

## Migration effect

The following capabilities move to `IMPLEMENTED`:

1. `methodology_registry`
2. `native_forecast_and_decision_execution`

The runtime migration contract therefore advances to 10 implemented capabilities and 3 planned capabilities.

## Remaining dependencies

The standalone Metals runtime must not be retired yet. The remaining required capabilities are:

1. universal package generation without an external Metals root;
2. a standalone-free readiness gate;
3. the complete GitHub Actions Metals production cycle.

## Certification rule

This block is certified only after:

- focused native-cycle tests pass;
- migration-contract tests pass;
- production and full regression suites pass;
- a strict native cycle succeeds against UIP-owned observations;
- the migration checker reports 10/13 implemented with no missing targets or external dependencies.
