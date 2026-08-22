# Universal Investment Platform — Project State

## Current status

```text
Project:
Universal Investment Platform

Project abbreviation:
UIP

Recovery classification:
RECOVERED_AND_GOVERNED

Current execution state:
DASHBOARD_PRODUCT_FOUNDATION_ACTIVE_ON_R3_CERTIFIED_AUTHORITY

Current roadmap phase:
Dashboard product foundation on certified R3 authority

Current milestone:
DASH_READ_1_CERTIFIED_PRESENTATION_READ_MODEL_PUBLICATION_CONTRACT

Current certification:
UIP_MTG_A1_EXPORT_ACCEPTANCE_PASS
UIP_MTG_A2_INTEGRATION_CERTIFICATION_PASS
UIP_METALS_A1_INTEGRATION_CERTIFICATION_PASS
UIP_CRYPTO_A1_INTEGRATION_CERTIFICATION_PASS
UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_CERTIFICATION_PASS
UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACT_CERTIFICATION_PASS
UIP_R2_REFRESHED_DATA_REHEARSAL_PASS
UIP_R3_METALS_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_PASS
UIP_R3_MTG_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_PASS
UIP_R3_CROSS_DOMAIN_RECONCILIATION_AND_CLOSEOUT_PASS
UIP_DASHBOARD_PRODUCT_SPECIFICATION_V1_APPROVED
UIP_DASHBOARD_V7_VISUAL_ACCEPTANCE_APPROVED

Next authorized action:
EXECUTE_DASH_READ_1_CERTIFIED_PRESENTATION_READ_MODEL_PUBLICATION_CONTRACT
```

## Repository authority

Primary repository:

`dlockar1mtg/UniversalInvestmentPlatform`

Stable branch:

`main`

Dashboard-governance branch:

`phase-uip-dashboard-product-spec-v1`

R3 merged main baseline used to create the dashboard-governance branch:

`cc2cfefb4c9135f0e93f20b2cb329d2347defdcf`

Current certified authoritative UIP database SHA-256:

`9af5e52882bdf61fed550a2ced9bc83ba1529c422633a7817660cf61d0e15a98`

Pre-migration-010 backup SHA-256:

`df7406361639e4b165afb8007f97feca60242e91d290c58ae521e423d82578cc`

Database classification:

`AUTHORITATIVE_MULTI_DOMAIN_PRODUCTION_STATE — R3_CERTIFIED`

## Approved dashboard product authority

Product specification:

`docs/project_control/UIP_DASHBOARD_PRODUCT_SPEC_V1.md`

Visual acceptance record:

`docs/project_control/UIP_DASHBOARD_V7_VISUAL_ACCEPTANCE.md`

Approved V7 artifact SHA-256:

`7403863ec8f662fbfbd293a3f19ac1d166dbde9bf79107da211f34da2c24d03a`

Approved primary navigation:

`Home | Recommendations | Portfolio | Transactions | Refresh | Operations`

Dashboard purpose:

- surface certified, domain-native investment recommendations in a user-friendly form;
- show what changed and what requires attention;
- track user holdings from an auditable transaction ledger;
- support manual buy/sell recording without automatic execution;
- expose portfolio value, pricing coverage, basis coverage, P/L, concentration, and history;
- expose refresh/data-health state and preserve the last certified authority on failure;
- preserve technical diagnostics under Operations rather than making them the primary user experience;
- allow Stocks/ETF and later domains to integrate through the same domain-neutral contracts without redesigning the shell.

## Certified domain authority

### Crypto

Current generic UIP authority:

- assets: `6`
- forecasts: `120`
- recommendations: `6`
- risk metrics: `6`
- platform registry: `crypto`
- latest import status: `IMPORTED`
- import health: `HEALTHY`

Crypto native recommendation semantics remain Crypto-owned. The dashboard may present them but may not silently redefine them into a universal scoring model.

### Metals

Current generic UIP authority:

- assets: `16`
- forecasts: `16`
- recommendations: `12`
- risk metrics: `11`
- platform registry: `metals`
- latest import status: `IMPORTED`
- import health: `HEALTHY`

Metals remains Metals-native in semantic ownership. Unsupported authority is not synthesized.

### MTG

Current analytical authority is native-only:

- native current rows: `968`
- native history rows: `968`
- generic MTG asset current rows: `0`
- generic MTG forecast current rows: `0`
- generic MTG recommendation current rows: `0`
- generic MTG risk current rows: `0`
- canonical platform registry ID: `mtg`
- adapter: `mtg-v1-native-authority-binding-1.0.0`
- package: `mtg-v1-native-authority-aa363cd474ae6b846588bb4a`
- run: `94c2bd3273eaba4d05ee8f7f5c3d6c4dcc283768`
- import: `84bcb0f3-ed3f-4d09-9957-22f8b3e236e9`
- latest import status: `IMPORTED`
- import health: `HEALTHY`

MTG lane populations remain:

- Collector V1: `50`
- Pre-Collector V1: `131`
- Secret Lair V1.1: `787`

Secret Lair remains a dynamic population. Native rank semantics and tied ranks remain native. BUY candidates do not constitute execution authority and must preserve the manual execution-price-check requirement where applicable.

## R3 cross-domain closeout

Status:

`UIP_R3_CROSS_DOMAIN_RECONCILIATION_AND_CLOSEOUT_PASS`

Migration:

`foundation/import_engine/sql/010_platform_registry_case_reconciliation.sql`

Certified effects:

- canonical mutable platform registry IDs are `crypto`, `metals`, and `mtg`;
- all three operational domain rows are complete and ACTIVE;
- all three latest imports are IMPORTED;
- all three import-health rows are HEALTHY;
- latest-successful and latest-attempt selectors expose one row per canonical domain;
- historical uppercase `MTG` lineage remains preserved;
- legacy uppercase MTG lineage rows mapped to canonical `mtg`: `19,679 / 19,679`;
- native lowercase MTG lineage rows mapped to canonical `mtg`: `969 / 969`;
- unmapped MTG lineage rows: `0`;
- migration 010 changed no append-only analytical history;
- migration 010 changed no Crypto or Metals analytical current authority;
- migration 010 is idempotent on the authoritative database.

Permanent evidence:

`docs/project_control/generated/r3_cross_domain_closeout/r3_cross_domain_closeout_certification.json`

Human-readable closeout:

`docs/project_control/R3_CROSS_DOMAIN_CLOSEOUT.md`

Disposition:

`UIP_R3_CERTIFIED_COMPLETE`

## Dashboard architecture boundaries

The next technical boundary is not a visual rewrite. It is a governed publication contract between certified analytical authority and the Render application.

Required separation:

### Analytical authority

- certified UIP/domain outputs;
- domain-native recommendations, forecasts, risk, ranks, current prices, lineage, and health;
- versioned/fingerprinted publication state.

### Application state

- user transactions;
- accounts and cash state;
- cost-basis correction metadata;
- watch/dismiss/acted/review-later state;
- UI preferences;
- sessions and roles.

Render/PostgreSQL must not independently reconstruct or reinterpret analytical authority. The intended next design is a versioned presentation/read-model publication from certified UIP authority into the hosted application boundary.

## Dashboard V1 semantic requirements

The following are mandatory implementation constraints:

- the Home hero is selected by an explicit UI-priority rule, not a universal cross-domain score;
- native source-domain status remains traceable separately from display labels;
- native MTG rank values are shown exactly as published; UIP does not invent common denominators or compare rank numbers across domains/lanes;
- unsupported horizons remain unavailable;
- price history is never presented as forecast history;
- portfolio-vs-benchmark comparison is historical unless a separately governed portfolio-level forecast model is certified;
- portfolio value exposes pricing coverage;
- portfolio return exposes cost-basis coverage and is labeled known-basis return while coverage is incomplete;
- unknown basis remains unknown rather than zero;
- descriptive allocation/concentration does not imply an allocation recommendation unless user policy or a separately governed allocation methodology exists;
- refresh remains fail-closed and preserves the last certified state;
- automatic purchase/sale execution remains prohibited.

## Stocks/ETF disposition

Stocks/ETF remains the next new analytical domain, but it is now required to integrate against the approved dashboard/read-model contracts rather than define the dashboard after the fact.

Until E1 certification:

- ETF holdings may exist in portfolio application state;
- ETF recommendation/forecast authority remains unavailable;
- UIP must not synthesize BUY/HOLD/forecast values for the future domain slot.

## Protected recovery resources

Historical recovery branches, archives, and local recovery resources remain evidence. They are not authorized for wholesale merge or destructive cleanup.

Previously identified protected local resources remain protected from unrelated work:

- `export_uip_interpretation_data.py`
- `uip_interpretation_export/`
- `uip_interpretation_input/`
- `uip_recovery_inspection/`
- `uip_recovery_inspection_output.txt`

## Current risks and outstanding work

1. `DASH-READ-1`: certify the presentation/read-model publication contract from authoritative UIP state to Render/PostgreSQL.
2. `DASH-SHELL-1`: implement the approved six-screen application shell and persistent health/freshness status.
3. `TXN-1`: implement the append-only transaction ledger and correction chain.
4. `PORT-1`: derive holdings, cost basis, P/L, historical performance, pricing coverage, and basis coverage.
5. `REC-UI-1`: publish certified Crypto, Metals, and MTG recommendation experiences without semantic reinterpretation.
6. `REFRESH-UI-1`: expose governed refresh requests, certification state, failure stage, scheduler, and last-good authority.
7. `OPS-1`: preserve current Render operations functionality under the approved Operations surface.
8. `UIP_E1_STOCKS_ETF_EXTENSION_BOUNDARY`: integrate Stocks/ETF through the approved contracts.
9. `DASH-CERT-1`: certify the full Render user experience against the product specification and V7 visual acceptance target.
10. Remote infrastructure selection and laptop-independent production certification remain outstanding after the dashboard is a known functioning system.

## Governance boundaries

The following remain prohibited unless separately governed and certified:

- universal cross-asset ranking;
- transferring native domain ranks or scores across domains;
- cross-domain investment weighting or allocation policy;
- interpreting missing values as zero, worst rank, WAIT, or any synthetic authority;
- automatic purchase or sale execution;
- treating model-qualified BUY candidates as execution-ready orders;
- silently redefining native forecast, recommendation, risk, or rank semantics.

Refresh remains separate from model retraining. Forecast-model validation remains separate from recommendation-policy validation.

## State principle

> UIP now has a certified R3 analytical foundation and an approved dashboard product target. Future implementation must connect those two through governed contracts: certified analytical truth flows into a versioned presentation model, user actions flow into an auditable application ledger, and future domains such as Stocks/ETF plug into the same interface without redefining existing authority.
