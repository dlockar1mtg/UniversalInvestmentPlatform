# Phase 8.4 — Unified Production Control Plane

Phase 8.4 adds one UIP-owned entry point for Metals, MTG, and Crypto production. Source repositories retain collection and model ownership. UIP owns invocation, fail-closed sequencing, universal import, unified status, and dashboard publication.

## Local configuration

```powershell
Copy-Item config\production_control_plane.example.json config\production_control_plane.local.json
```

The local configuration includes repository paths and the Crypto DuckDB path. Operators no longer need to set a temporary Crypto environment variable.

## Commands

```powershell
python scripts\run_unified_production_cycle.py --platforms all
python scripts\run_unified_production_cycle.py --platforms crypto
python scripts\run_unified_production_cycle.py --platforms metals,mtg
```

The default is fail-closed. A failed platform stops later platforms. `--continue-on-failure` is reserved for diagnostic runs.

## Unified evidence

Runtime evidence is written to:

- `data/operations/production_control_plane/latest.json`
- `data/operations/production_control_plane/platform_status.csv`
- `data/operations/production_control_plane/history/<cycle_id>.json`

## Repository hygiene

`data/integration/*` and `data/operations/*` are runtime directories. Previously committed Crypto runtime packages must be removed from the Git index once. Future production cycles must leave `git status` clean.

Phase 8.4 is certified when focused tests pass, individual platform runs pass, the all-platform cycle passes, unified status is published, and the working tree remains clean.
