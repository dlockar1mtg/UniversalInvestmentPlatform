# UIP R3 — Cross-Domain Reconciliation and Closeout

## Status

`UIP_R3_CROSS_DOMAIN_RECONCILIATION_AND_CLOSEOUT_PASS`

R3 is certified complete across Crypto, Metals, and MTG. The three domains coexist in the authoritative UIP database with distinct native semantics, complete operational registry coverage, preserved lineage, no competing MTG generic current authority, and no universal ranking, allocation, or automatic-execution policy.

## Authoritative database

Pre-migration-010 SHA-256:

`df7406361639e4b165afb8007f97feca60242e91d290c58ae521e423d82578cc`

Post-migration-010 authoritative SHA-256:

`9af5e52882bdf61fed550a2ced9bc83ba1529c422633a7817660cf61d0e15a98`

Retained pre-migration-010 backup SHA-256:

`df7406361639e4b165afb8007f97feca60242e91d290c58ae521e423d82578cc`

Migration `010_platform_registry_case_reconciliation.sql` was rehearsed on a byte-identical scratch database, then applied to the authoritative database and applied a second time to prove idempotence.

## Current analytical authority

Generic UIP current surfaces remain domain-specific for Crypto and Metals:

| Surface | Crypto | Metals | Generic MTG |
| --- | ---: | ---: | ---: |
| asset master | 6 | 16 | 0 |
| forecasts | 120 | 16 | 0 |
| recommendations | 6 | 12 | 0 |
| risk metrics | 6 | 11 | 0 |

MTG remains native-only for analytical authority:

- native current rows: `968`
- native history rows: `968`
- generic MTG analytical current rows: `0`

No R3 closeout step translated MTG native rank or purchase semantics into generic UIP recommendation, forecast, risk, or rank authority.

## Platform registry and operational health

The mutable operational registry is now canonical:

- `crypto`
- `metals`
- `mtg`

All three domains are:

- registry status: `ACTIVE`
- last import status: `IMPORTED`
- import health: `HEALTHY`
- warning count: `0`
- error count: `0`

MTG now reports its certified native authority rather than the recovery-era handoff adapter:

- adapter: `mtg-v1-native-authority-binding-1.0.0`
- package: `mtg-v1-native-authority-aa363cd474ae6b846588bb4a`
- run: `94c2bd3273eaba4d05ee8f7f5c3d6c4dcc283768`
- import: `84bcb0f3-ed3f-4d09-9957-22f8b3e236e9`

Package ID, run ID, and import ID are separate lineage identities and are intentionally preserved as distinct fields.

## MTG case reconciliation

Historical recovery evidence remains preserved under its original uppercase `MTG` platform identity. Current operational identity is canonical lowercase `mtg`.

`universal_lineage_with_domain` now maps both variants case-insensitively to the canonical `mtg` domain:

- legacy uppercase `MTG` lineage rows: `19,679`
- mapped to canonical MTG domain: `19,679`
- native lowercase `mtg` lineage rows: `969`
- mapped to canonical MTG domain: `969`
- unmapped MTG lineage rows: `0`

No historical import, package, platform-status, or analytical history row was rewritten to manufacture a lowercase historical identity.

## History preservation

Migration 010 changed no append-only analytical history:

- asset master history: `8,199`
- forecasts history: `5,254`
- recommendations history: `5,285`
- risk metrics history: `2,439`
- platform-status history: `25`
- MTG native-authority history: `968`

All pre/post fingerprints matched during authoritative certification.

## Current-import selectors

`universal_latest_successful_import` and `universal_latest_import_attempt` now reconcile platform identity case-insensitively and expose exactly one current row for each domain:

- Crypto: `1`
- Metals: `1`
- MTG: `1`

This is an operational current-state correction only; historical import rows retain their original platform identity.

## Semantic and execution boundaries

R3 closeout preserves the following restrictions:

- native domain semantics remain authoritative;
- missing values are not synthesized;
- no universal cross-domain rank exists;
- no cross-domain investment weighting or allocation policy exists;
- no automatic execution authority exists;
- MTG execution-ready purchase authority remains false;
- MTG BUY candidates remain native model-qualified candidates rather than universal execution instructions.

## Permanent evidence

`docs/project_control/generated/r3_cross_domain_closeout/r3_cross_domain_closeout_certification.json`

Supporting domain evidence:

- `docs/project_control/generated/crypto_a1_integration/crypto_a1_integration_certification.json`
- `docs/project_control/generated/r3_metals_domain_health/metals_r3_domain_health_certification.json`
- `docs/project_control/generated/r3_mtg_domain_health/mtg_r3_domain_health_certification.json`

## Disposition

`UIP_R3_CERTIFIED_COMPLETE`

## Next authorized gate

`UIP_E1_STOCKS_ETF_EXTENSION_BOUNDARY`

The Stocks/ETF extension must define its own source authority, contract, population semantics, forecast/recommendation/risk semantics, lineage, and certification. It may join the common UIP interface without inheriting Crypto, Metals, or MTG scoring, ranking, weighting, or execution semantics.
