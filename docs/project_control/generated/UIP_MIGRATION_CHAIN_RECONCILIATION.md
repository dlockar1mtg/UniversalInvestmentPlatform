# UIP Ordered Migration Chain Reconciliation Report

## Inspection scope

- Generated: `2026-07-30T18:19:05.195624+00:00`
- Current database: `C:\Users\DevonLockard\InvestmentPlatform\data\universal\universal_investment.duckdb`
- Current database SHA-256 before inspection: `dcc390bba481d649f591847ec32332f725b0b62473dcc4104d51e8c532076116`
- Current database SHA-256 after inspection: `dcc390bba481d649f591847ec32332f725b0b62473dcc4104d51e8c532076116`
- Current database opened read-only: `true`
- Reconstruction database: temporary disposable DuckDB file

## Active migration chain

| Order | File | SHA-256 | Size |
|---:|---|---|---:|
| 1 | `foundation/import_engine/sql/001_initialize_universal_database.sql` | `702d1e48edb79d6c0595586b12332619d71d4cb87201f3c3a12d40c1409225da` | 9954 |
| 2 | `foundation/import_engine/sql/002_audit_registry_integration.sql` | `9563d6ca0a0b120d4de15a6fd78d47fd4d3f4c5afa530886a8289c8011b1cc5d` | 2735 |
| 3 | `foundation/import_engine/sql/003_health_status_latest_attempt.sql` | `130f47a6e95bbc8e2479466e2ea6f42d05e726f7fc22f94fd4a2f96fdbef7624` | 880 |
| 4 | `foundation/import_engine/sql/004_historical_performance.sql` | `ae86fefd6113eb98d2a87f293797e34d4216001d7d55ba21276185d202c40041` | 1728 |

## Preserved non-authoritative SQL evidence


## Backup comparison

- Canonical `002` equals preserved backup: `none`
- Canonical-only lines: `79`
- Backup-only lines: `0`

## Temporary baseline upgrade

- Execution result: `PASS`
- Executed files: `4`
- Baseline objects: `23`
- Upgraded objects: `25`

## Fresh reconstruction

- Execution result: `PASS`
- Executed files: `4`
- Reconstructed objects: `25`

## Schema comparison

- Exact object, column, constraint, index, and view-definition match: `true`

### Missing from reconstruction

- None

### Extra in reconstruction

- None

### Definition mismatches

- None

## Reconciliation disposition

`MIGRATION_CHAIN_REPRODUCES_UPGRADED_SCHEMA`

No production database changes were made.
