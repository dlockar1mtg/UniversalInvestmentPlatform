# Phase 10.11 — MTG Import and Reconciliation

## Objective

Import the certified MTG Phase 10.10 package into the Universal Investment Platform without changing the source package or weakening the Universal Import Engine contracts.

## Architecture

The certified MTG export uses `export_manifest.json` and lane-aware forecast columns. The Universal Import Engine requires `export_manifest.csv` and the canonical v1 database schemas. Phase 10.11 adds a non-destructive adapter that:

1. Validates the source package status, hashes, product count, diagnostics, and privacy boundary.
2. Creates a canonical Universal Integration Package under `data/integration/mtg/latest`.
3. Expands lane-aware forecasts into canonical forecast observations.
4. Preserves all 1,141 universal MTG asset identities.
5. Imports the package transactionally through the existing import engine.
6. Reconciles source, adapted-package, audit-registry, and DuckDB history counts.
7. Keeps position-level holdings out of the import.

## Expected canonical datasets

| Dataset | Expected rows |
|---|---:|
| asset_master | 1,141 |
| forecasts | 1,363 |
| recommendations | 1,141 |
| risk_metrics | 1,141 |
| platform_status | 1 |
| **Total** | **4,787** |

Forecast expansion consists of 973 Secret Lair native forecasts plus three horizons for 47 Collector Booster Boxes and 83 Pre-Collector Booster Boxes.

## Privacy boundary

The source package contains only three lane-level portfolio summary rows. Phase 10.11 does not create or import `portfolio_positions.csv`. Position quantities, acquisition dates, holding IDs, individual cost basis, and personal notes remain outside the Universal database import.

## Duplicate behavior

The Universal Import Engine remains authoritative for duplicate protection. A first run imports the package. A later run against the same source package reports `ALREADY_IMPORTED` and reconciles the existing successful import instead of duplicating history rows.

## Runtime outputs

Generated outputs are local and excluded from commits:

- `data/integration/mtg/latest/`
- `data/universal/universal_investment.duckdb`
- `data/validation/imports/mtg_phase_10_11/`

## Certification requirements

- Source products: 1,141
- Source forecast eligible: 1,103
- Source recommendation eligible: 694
- Adapted package integrity: PASS
- Imported datasets: 5
- Imported rows: 4,787
- Asset identities: 1,141 unique
- Recommendation and risk identities equal the asset universe
- Forecast identities are a subset of the asset universe
- Position-level holdings imported: No
- Universal import errors: 0
- API quota calls: 0
