# MTG Orchestration Architecture Decision

Generated: 2026-07-31T12:12:29.284592+00:00

## Decision

The Universal Investment Platform will not absorb or directly execute the standalone MTG production orchestration chain.

The MTG source domain remains responsible for:

- marketplace and pricing collection;
- eBay and TCGCSV collection;
- Secret Lair production refreshes;
- MTG historical-data production;
- domain-specific marketplace production.

UIP is responsible for:

- validating a certified MTG delivery package;
- importing universal-contract datasets transactionally;
- preserving package and row lineage;
- publishing current universal views;
- exposing imported MTG data to UIP decision orchestration;
- rejecting incomplete, stale, incompatible, or uncertified packages.

## Boundary rule

UIP must consume certified MTG artifacts through universal contracts. UIP must not call the standalone MTG collectors, production scripts, aggregate runners, repair scripts, or legacy Terminal 2 lifecycle directly.

## Disposition counts

- `ADAPT`: 9
- `REPLACE`: 4
- `RETAIN_STANDALONE`: 5

## Compatibility decisions

| Source script | Final disposition | Rationale |
|---|---|---|
| `terminal2_lifecycle.py` | `REPLACE` | UIP already owns platform-level orchestration; do not port a second aggregate runner. |
| `terminal2_run_all.py` | `REPLACE` | UIP already owns platform-level orchestration; do not port a second aggregate runner. |
| `scripts/build_mtg_uip_export.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |
| `scripts/build_phase_10_10_universal_export.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |
| `scripts/run_certified_marketplace_decisioning.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |
| `run.py` | `REPLACE` | UIP already owns platform-level orchestration; do not port a second aggregate runner. |
| `scripts/run_phase_11e_12_accumulation_cycle.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |
| `scripts/run_phase_11e_13_valuation_integration.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |
| `scripts/run_phase_11e_14_consumption_integration.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |
| `scripts/run_mtg_marketplace_production.py` | `RETAIN_STANDALONE` | Domain production collection remains outside UIP; expose certified outputs through contracts. |
| `scripts/run_phase_11e_15_production_delivery.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |
| `scripts/run_universal_mtg_history_production.py` | `RETAIN_STANDALONE` | Domain production collection remains outside UIP; expose certified outputs through contracts. |
| `scripts/run_daily_ebay_collection.py` | `RETAIN_STANDALONE` | Domain production collection remains outside UIP; expose certified outputs through contracts. |
| `scripts/run_daily_tcgcsv_collection.py` | `RETAIN_STANDALONE` | Domain production collection remains outside UIP; expose certified outputs through contracts. |
| `scripts/run_secret_lair_production_refresh.py` | `RETAIN_STANDALONE` | Domain production collection remains outside UIP; expose certified outputs through contracts. |
| `terminal2_daily_update.py` | `REPLACE` | UIP already owns platform-level orchestration; do not port a second aggregate runner. |
| `scripts/build_mtg_hosted_uip_delivery.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |
| `scripts/run_phase_11e_17_manual_uip_handoff.py` | `ADAPT` | Potentially reusable boundary or handoff logic, but paths, execution, and contracts require UIP alignment. |

## First approved implementation slice

Build a UIP-native MTG package intake orchestrator that:

1. accepts an explicit MTG package directory;
2. validates its manifest and universal contract files;
3. initializes or upgrades a caller-selected temporary database;
4. imports historical performance and existing universal MTG datasets;
5. records package and row lineage;
6. produces an immutable intake result;
7. never invokes standalone MTG production scripts;
8. never modifies the production UIP database during certification.

## Explicit exclusions

- No wholesale copy of `terminal2_run_all.py`.
- No copy of `terminal2_daily_update.py`.
- No UIP invocation of eBay, TCGCSV, or marketplace collectors.
- No automatic scheduler in this implementation slice.
- No merge of the old Phase 10.12 recovery branch.
- No modification of the certified production DuckDB.
