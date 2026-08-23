# DASH-READ-1 — Certified Presentation / Read-Model Publication Contract

## Status

`IMPLEMENTATION_CANDIDATE — REQUIRES CERTIFICATION`

## Milestone

`DASH_READ_1_CERTIFIED_PRESENTATION_READ_MODEL_PUBLICATION_CONTRACT`

## Purpose

DASH-READ-1 defines the governed analytical boundary between the certified UIP production authority and the hosted Render application.

The approved flow is:

`Certified UIP analytical authority → versioned presentation publication → hosted PostgreSQL read model → authenticated read API → V7 dashboard`

The hosted presentation store is **not** a second analytical authority. It may only expose a versioned projection of already-certified current authority.

## Governing source state

Current certified analytical classification:

`AUTHORITATIVE_MULTI_DOMAIN_PRODUCTION_STATE — R3_CERTIFIED`

Current certified R3 database fingerprint remains recorded by Project Control. DASH-READ-1 requires each actual publication to record the source database SHA-256 rather than embedding one permanent database hash in the contract.

## Domain authority mapping

### Crypto

Authority mode:

`GENERIC_CURRENT_VIEWS`

Presentation inputs:

- `asset_master_current`
- `forecasts_current`
- `recommendations_current`
- `risk_metrics_current`
- `universal_domain_operational_status`
- `universal_lineage_with_domain`

Crypto native recommendation/model semantics remain source-owned. The generic UIP views are the certified integration boundary; DASH-READ-1 does not reinterpret them.

### Metals

Authority mode:

`GENERIC_CURRENT_VIEWS`

Presentation inputs:

- `asset_master_current`
- `forecasts_current`
- `recommendations_current`
- `risk_metrics_current`
- `universal_domain_operational_status`
- `universal_lineage_with_domain`

Metals remains UIP-native in ownership, but its presentation fields are still projected from certified current authority only.

### MTG

Authority mode:

`MTG_NATIVE_CURRENT_ONLY`

Presentation inputs:

- `mtg_native_authority_current`
- `universal_domain_operational_status`
- `universal_lineage_with_domain`

The four generic MTG current analytical views must remain zero-authority for MTG:

- `asset_master_current`
- `forecasts_current`
- `recommendations_current`
- `risk_metrics_current`

MTG lane, native rank, purchase status, purchase semantic, actionability, price authority, forecast authority, execution-price-check requirement, and native authority pointers remain MTG-owned semantics.

## Current-price boundary

DASH-READ-1 binds MTG current price directly because `mtg_native_authority_current` contains an explicit governed current-price field and availability flag.

The generic Crypto and Metals current views do **not** expose one canonical first-class current-price column in the universal schema. Therefore DASH-READ-1 deliberately records their current-price contract as:

`NOT_BOUND_IN_DASH_READ_1_GENERIC_SURFACE`

This is a governed gap, not permission to scrape a price from arbitrary metadata or reinterpret a forecast point as current price. A later presentation adapter may bind a current-price source only after its authority is explicitly proven.

## Publication metadata

Every hosted publication must carry:

- `publication_id`
- `publication_version`
- `source_database_sha256`
- `source_database_classification`
- `published_at_utc`
- `publication_status`

A publication that cannot identify its source analytical fingerprint is invalid.

## Atomic publication rule

Production publication must use a stage / validate / activate boundary.

Required behavior:

1. create a new inactive publication version;
2. write all contracted projections into that version;
3. validate required domains, field presence, lineage, health and counts;
4. mark the publication complete only after validation passes;
5. atomically switch the hosted active-publication pointer;
6. preserve the prior active publication if any step fails.

Partial domain activation is not authorized by DASH-READ-1.

## Missing and unsupported authority

The hosted read model must preserve absence.

It must not:

- convert missing forecast authority into zero;
- convert missing recommendation authority into HOLD or WAIT;
- convert unknown cost basis into zero;
- invent current price from a forecast;
- invent native rank denominators;
- manufacture confidence/risk fields;
- extrapolate unsupported forecast horizons;
- create a universal cross-domain score.

## Native rank rule

MTG may expose `native_rank` and `native_rank_type` exactly as native authority publishes them.

Crypto and Metals have no DASH-READ-1 native-rank contract.

Rank values may not be compared across domains or used as a hidden universal recommendation score.

## Read API contract

DASH-READ-1 reserves five authenticated analytical read surfaces for the V7 application:

1. `global_status`
2. `recommendations`
3. `asset_detail`
4. `domain_health`
5. `lineage`

The exact HTTP route implementation is a later implementation step, but it must be backed by one active presentation publication version and must expose source publication/freshness metadata.

## Application state boundary

The following are intentionally outside DASH-READ-1 analytical publication authority:

- transactions;
- holdings derived from transactions;
- accounts;
- cash balances;
- watchlist state;
- dismissed / acted / review-later state;
- user target/allocation policy;
- UI preferences.

These belong to hosted application state and must remain distinguishable from analytical authority.

## Refresh ownership

DASH-READ-1 does not change R1 refresh ownership.

- Crypto source/model execution remains Crypto-owned.
- MTG source/model execution remains MTG-owned.
- Metals remains UIP-native.
- UIP may orchestrate governed workflows but may not bypass source-owned collectors.
- failed source refresh or failed presentation publication preserves last certified authority.

## V7 dashboard implications

The V7 dashboard may show:

- certified native recommendation/status;
- current price only where governed authority exists;
- forecasts only where governed authority exists;
- risk/confidence only where governed authority exists;
- native rank only where governed authority exists;
- data freshness and health;
- lineage/provenance;
- recommendation-change presentation after history contract is implemented.

It must visibly distinguish:

- certified/current;
- stale but last-certified;
- unsupported;
- unavailable;
- future domain not active.

## Explicit prohibitions

DASH-READ-1 authorizes none of the following:

- universal cross-asset ranking;
- cross-domain allocation or target weighting;
- automatic buy/sell execution;
- semantic transfer between domains;
- model retraining;
- replacing certified source authority with Render/PostgreSQL calculations.

## Certification gate

DASH-READ-1 may be certified only after tests prove:

1. the machine-readable contract loads fail-closed;
2. exactly Crypto, Metals and MTG are bound;
3. contracted source fields exist in a freshly initialized UIP database;
4. MTG uses native authority and generic MTG current analytical authority remains prohibited;
5. missing/unsupported synthesis remains prohibited;
6. presentation storage is explicitly projection-only;
7. atomic last-good-state preservation is required;
8. application-state fields remain outside analytical authority;
9. the production analytical database is not modified by contract validation.

Completion state:

`DASH_READ_1_CERTIFIED_PRESENTATION_READ_MODEL_PUBLICATION_CONTRACT_PASS`
