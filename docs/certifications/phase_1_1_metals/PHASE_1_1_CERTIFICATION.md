# Phase 1.1 Certification — Metals

## Decision

**PASS — Metals is selected and frozen as the first real Universal platform integration target.**

## Evidence reviewed

- Complete supplied project archive
- Current-state and v8 documentation
- Runtime configuration and entry points
- Core package structure and tests
- DuckDB schema: 72 base tables, 48 views
- Active v8 exports and report artifacts
- v8 orchestration and exporter source code

## Certified integration surface

The supported source interface is the v8 latest-state export layer, augmented in Phase 1.2 by read-only exports for portfolio positions and risk metrics. The Universal platform will consume a transformed contract package, not the native database.

## Exit criteria status

- First platform selected: complete
- Current version/status frozen: complete
- Repository and module map: complete
- Data flow documented: complete
- Database inventory: complete
- Output inventory: complete
- Run order documented: complete
- Native-to-Universal mapping: complete
- Integration boundary frozen: complete

## Phase 1.2 authorization

Proceed to **Phase 1.2 — Build the Metals Universal Export Adapter**.

Recommended first implementation files:

- `exchange/metals/config/asset_crosswalk.csv`
- `exchange/metals/scripts/export_universal_metals.py`
- `exchange/metals/tests/test_metals_adapter.py`
- `data/integration/metals/<run_id>/` for generated packages

The adapter should initially emit `asset_master`, `forecasts`, `recommendations`, `risk_metrics`, `portfolio_positions`, `platform_status`, and `export_manifest`.
