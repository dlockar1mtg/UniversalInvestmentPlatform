# Phase 1.1 — Metals Integration Freeze Package

This package completes **Phase 1.1 — Select and Freeze the First Integration Target** for the Universal Investment Intelligence Platform.

## Certified target

- Platform: Metals Intelligence Platform
- Integration role: Platform #1
- Frozen release: v8.1 (repository state supplied July 2026)
- Database: DuckDB
- Supported integration boundary: versioned CSV export adapter
- Source modification policy: non-destructive; Universal must not read internal tables directly in production

## Deliverables

- `CURRENT_STATE.md`
- `PLATFORM_MAP.md`
- `DATA_FLOW.md`
- `DATABASE_MAP.md`
- `OUTPUT_INVENTORY.md` and `OUTPUT_INVENTORY.csv`
- `RUN_ORDER.md`
- `UNIVERSAL_MAPPING.md`
- `INTEGRATION_BOUNDARY.md`
- `PHASE_1_1_CERTIFICATION.md`
- machine-readable database and file inventories

The next phase should build a Metals export adapter that writes universal-contract files plus an export manifest into a staging folder controlled by the Universal platform.
