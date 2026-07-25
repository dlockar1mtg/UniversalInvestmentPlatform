# Phase 8.9.9.2 — UIP-Native Metals Persistence and Ingestion

## Objective

Persist benchmark and investable-vehicle observations inside the Universal Investment Platform without reading the standalone Metals DuckDB or export directory.

## Implemented surfaces

- `foundation/production/metals_native_store.py`
  - DB-API persistence boundary;
  - PostgreSQL `format` and SQLite `qmark` parameter styles;
  - idempotent observation upserts;
  - durable run records;
  - explicit PASS and FAILED completion states;
  - latest observation summaries.
- `foundation/production/metals_native_ingestion.py`
  - normalizes UIP-owned benchmark and vehicle CSV surfaces;
  - validates required identifiers, dates, values, and provenance;
  - persists one fail-closed native run.
- `scripts/ingest_metals_native_observations.py`
  - uses `UIIP_DATABASE_URL` and PostgreSQL when configured;
  - uses a local SQLite development database otherwise;
  - requires no `--metals-root` argument.

## Data ownership

The production system of record is PostgreSQL through `UIIP_DATABASE_URL`. GitHub-hosted workflows may create transient files during collection, but durable observations and run state belong in the UIP database.

The local SQLite fallback exists for development and deterministic testing only.

## Retirement impact

This implementation replaces the legacy `data/metals_intelligence.duckdb` responsibility for newly collected observations. It does not yet migrate historical rows, execute native forecasts, or build the final Universal package without an external root.

Therefore the runtime migration contract advances native observation persistence to `IMPLEMENTED` while the overall migration remains `INCOMPLETE`.

## Validation commands

```powershell
python -m pytest tests\production\test_metals_native_store.py -q
python -m pytest tests\production -q
python -m pytest -q
python scripts\check_metals_runtime_migration.py
```

Expected migration baseline after this step:

- implemented capabilities: 8 of 13;
- planned capabilities: 5;
- missing implemented targets: 0;
- external runtime dependencies in completed targets: 0;
- overall status: `INCOMPLETE`.

## Next block

Phase 8.9.9.3 will provide the methodology registry and UIP-native forecast/decision execution over the native observation store.
