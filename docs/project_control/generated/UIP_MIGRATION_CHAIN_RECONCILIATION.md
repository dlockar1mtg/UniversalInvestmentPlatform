# UIP Ordered Migration Chain Reconciliation Report

## Inspection scope

- Generated: `2026-07-30T17:40:01.337876+00:00`
- Current database: `data/universal/universal_investment.duckdb`
- Current database SHA-256: `dcc390bba481d649f591847ec32332f725b0b62473dcc4104d51e8c532076116`
- Current database opened read-only: `true`
- Reconstruction database: temporary disposable DuckDB file

## Active migration chain

| Order | File | SHA-256 | Size |
|---:|---|---|---:|
| 1 | `foundation/import_engine/sql/001_initialize_universal_database.sql` | `702d1e48edb79d6c0595586b12332619d71d4cb87201f3c3a12d40c1409225da` | 9954 |
| 2 | `foundation/import_engine/sql/002_audit_registry_integration.sql` | `9563d6ca0a0b120d4de15a6fd78d47fd4d3f4c5afa530886a8289c8011b1cc5d` | 2735 |
| 3 | `foundation/import_engine/sql/003_health_status_latest_attempt.sql` | `130f47a6e95bbc8e2479466e2ea6f42d05e726f7fc22f94fd4a2f96fdbef7624` | 880 |

## Preserved non-authoritative SQL evidence

- `foundation/import_engine/sql/002_audit_registry_integration_before_1_3_6_2_20260717_085304.sql` — SHA-256 `ff69495d866b47cc0da9290a6b1ab90f7022d7508b5c24c4529eb8968eea046b`

## Backup comparison

- Canonical `002` equals preserved backup: `false`
- Canonical-only lines: `7`
- Backup-only lines: `3`

## Fresh reconstruction

- Execution result: `PASS`
- Executed files: `3`
- Reconstructed objects: `23`
- Current objects: `23`

## Schema comparison

- Exact object, column, constraint, index, and view-definition match: `true`

### Missing from reconstruction

- None

### Extra in reconstruction

- None

### Definition mismatches

- None

## Reconciliation disposition

`MIGRATION_CHAIN_REPRODUCES_CURRENT_SCHEMA`

No production database changes were made.
