# DASH-READ-1 Versioned Presentation Publication Model

Status: IMPLEMENTED FOR REHEARSAL

## Purpose

Publish certified UIP analytical current state into the hosted PostgreSQL/Render boundary without making PostgreSQL a second analytical authority.

Source analytical authority remains the certified UIP DuckDB and source-owned domain semantics.

## Flow

`certified UIP authority -> build immutable publication bundle -> validate semantics -> stage PostgreSQL version -> validate staged version -> atomically activate pointer`

A failed stage, validation, or activation must leave the previously active presentation publication unchanged.

## PostgreSQL objects

- `presentation_publications`: immutable publication metadata and status.
- `presentation_records`: version-scoped normalized presentation records stored as JSONB payloads.
- `presentation_active_publication`: singleton pointer to the currently active presentation version.

The active pointer changes in the same transaction that marks the new publication ACTIVE and supersedes the previous version.

## Published record classes

- `domain_health`
- `asset`
- `recommendation`
- `forecast`
- `risk`
- `native_authority` for MTG native evidence

Every analytical record stays scoped to a publication ID and domain ID and carries source lineage fields where the underlying authority provides them.

## Domain rules

### Crypto and Metals

Authority remains the generic current UIP analytical views.

DASH-READ-1 does not yet bind a first-class current-price authority for these domains. Asset presentation records therefore publish:

- `current_price_usd = null`
- `current_price_authority_available = false`
- `current_price_authority_state = NOT_BOUND_IN_DASH_READ_1_GENERIC_SURFACE`

Forecast values must not be substituted for current prices.

### MTG

Authority remains `mtg_native_authority_current` only.

The publication preserves:

- MTG lane;
- current-price availability and current price when authoritative;
- native rank and rank type;
- native purchase status and purchase semantic;
- actionability/evidence state;
- manual execution-price-check requirement;
- native authority pointer/SHA;
- no automatic purchase execution;
- forecast fields only when forecast authority is explicitly available.

No generic MTG current analytical authority is reintroduced.

## Fail-closed semantic validation

Before staging, the publication service requires:

- exactly Crypto, Metals, and MTG health records;
- all three domains CERTIFIED / ACTIVE / IMPORTED with zero warnings/errors;
- native semantics authoritative for all three;
- cross-asset ranking unauthorized;
- automatic execution unauthorized;
- a non-empty current asset surface for every certified domain;
- no synthesized Crypto/Metals current price;
- no presentation cross-domain rank;
- MTG asset projection reconciling to MTG native-authority records;
- MTG automatic purchase execution false.

## Dynamic population rule

The PostgreSQL publication store intentionally does not hard-code 968 MTG rows or any other permanent asset count. Current population counts are certified at the applicable source/analytical milestone and may change as dynamic asset universes change. A rehearsal against the current R3 baseline may assert the present 968-row population, but the reusable presentation-store contract must not make that count permanent.

## Application-state boundary

This model does not store transaction-ledger state, user accounts, cash balances, watchlist state, portfolio policy, or UI preferences. Those remain separate hosted application state and will be implemented in later dashboard milestones.

## Next certification gate

Rehearse bundle construction from the authoritative R3 DuckDB and prove:

1. source database is opened read-only;
2. source SHA remains byte-identical;
3. publication bundle contains the certified current domain populations;
4. Crypto/Metals prices remain explicitly unavailable pending governed bindings;
5. MTG native semantics reconcile exactly;
6. semantic validation passes;
7. the PostgreSQL storage contract passes regression tests;
8. no analytical authority is mutated.
