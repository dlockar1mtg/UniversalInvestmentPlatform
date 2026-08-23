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
DASHBOARD_APPLICATION_SHELL_ACTIVE_ON_CERTIFIED_PRESENTATION_AUTHORITY

Current roadmap phase:
Dashboard product foundation on certified R3 authority

Current milestone:
DASH_SHELL_1_APPROVED_V7_APPLICATION_SHELL

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
DASH_READ_1_CERTIFIED_COMPLETE

Next authorized action:
IMPLEMENT_DASH_SHELL_1_APPROVED_V7_APPLICATION_SHELL
```

## Repository authority

Primary repository:

`dlockar1mtg/UniversalInvestmentPlatform`

Stable branch:

`main`

DASH-READ-1 merged production commit:

`497e92f4c49b2ce84413035840e74305e92bbaed`

Active implementation branch:

`phase-uip-dash-shell-1`

Current certified authoritative UIP database SHA-256:

`9af5e52882bdf61fed550a2ced9bc83ba1529c422633a7817660cf61d0e15a98`

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

## DASH-READ-1 certified hosted authority

Status:

`DASH_READ_1_CERTIFIED_COMPLETE`

Permanent evidence:

- `docs/project_control/DASH_READ_1_CERTIFICATION.md`
- `docs/project_control/generated/dash_read_1/dash_read_1_certification.json`

Active hosted publication:

- publication ID: `dash-read-1-r3-certified-postgres-9af5e52882bd`
- publication version: `1.0.0`
- content fingerprint: `cc3ab02cf9e7411641e384d27fd2ec48bf687ec98d7fa191ddcc6ff3b768bd3f`
- record count: `4031`
- source database SHA-256: `9af5e52882bdf61fed550a2ced9bc83ba1529c422633a7817660cf61d0e15a98`
- publication state: `ACTIVE`

Certified hosted read endpoints:

- `/v1/presentation/status`
- `/v1/presentation/domain-health`
- `/v1/presentation/recommendations`
- `/v1/presentation/assets/{domain_id}/{asset_id}`
- `/v1/presentation/lineage/{domain_id}/{asset_id}`

Hosted closure proved Render `LIVE` and `READY`, authentication fail-closed behavior, exact active-publication provenance, readable domain health, recommendation populations of Crypto `6`, Metals `12`, MTG `968`, readable MTG asset detail and lineage, no cross-domain ranking, no automatic execution, and rejection of the uncertified future Stocks domain.

## Certified domain authority

### Crypto

- assets: `6`
- forecasts: `120`
- recommendations: `6`
- risk metrics: `6`
- current-price presentation authority: not yet bound in DASH-READ-1 generic surface
- import health: `HEALTHY`

### Metals

- assets: `16`
- forecasts: `16`
- recommendations: `12`
- risk metrics: `11`
- current-price presentation authority: not yet bound in DASH-READ-1 generic surface
- import health: `HEALTHY`

### MTG

- native current rows: `968`
- native history rows: `968`
- hosted presentation forecasts: `931`
- generic MTG analytical current authority: `0`
- current-price authority: native when available
- canonical platform registry ID: `mtg`
- import health: `HEALTHY`

MTG lane populations remain Collector `50`, Pre-Collector `131`, Secret Lair `787`. Secret Lair is dynamic. Native rank semantics remain native and BUY candidates do not authorize automatic execution.

## Dashboard architecture boundary

Certified analytical authority and hosted application state remain separate.

Analytical authority includes certified domain outputs, recommendations, forecasts, risk, native ranks, prices where authority exists, lineage, health, and versioned publication provenance.

Application state will include user transactions, accounts, cash, cost-basis correction metadata, watch/dismiss/acted/review-later state, UI preferences, sessions, and roles.

Render/PostgreSQL may present certified authority but may not independently recreate, reinterpret, rank, or fill missing analytical values.

## DASH-SHELL-1 scope

DASH-SHELL-1 is authorized to implement the approved V7 shell on Render with:

- six-screen navigation: Home, Recommendations, Portfolio, Transactions, Refresh, Operations;
- persistent global health/freshness status;
- authentication-aware application shell;
- responsive desktop/mobile layout;
- V7 design tokens, hierarchy, panels, states, and drawer patterns;
- real DASH-READ-1 global status/domain-health data where already supported;
- explicit empty/not-yet-implemented states for workflows owned by later milestones;
- preservation of the existing technical dashboard capability for later placement under Operations.

DASH-SHELL-1 must not prematurely implement transaction accounting, portfolio basis/P&L logic, recommendation reinterpretation, refresh execution, or ETF authority. Those remain owned by later milestones.

## Dashboard semantic requirements

Mandatory constraints remain:

- Home hero priority is UI relevance, not a universal cross-domain score;
- native source-domain status remains traceable separately from display labels;
- native MTG rank values are rendered exactly as published;
- unsupported horizons remain unavailable;
- price history is never forecast history;
- benchmark comparison is historical unless separately governed;
- portfolio value must expose pricing coverage;
- incomplete basis must expose known-basis coverage;
- unknown basis is never zero;
- concentration is descriptive unless a user policy exists;
- refresh remains fail-closed with last-good-state preservation;
- automatic trading remains prohibited.

## Stocks/ETF disposition

Stocks/ETF remains the next new analytical domain after the core dashboard product workflow milestones. Until E1 certification, ETF holdings may later exist as application state, but no ETF recommendation or forecast authority may be synthesized.

## Protected recovery resources

Previously identified protected local resources remain protected from unrelated work:

- `export_uip_interpretation_data.py`
- `uip_interpretation_export/`
- `uip_interpretation_input/`
- `uip_recovery_inspection/`
- `uip_recovery_inspection_output.txt`

## Current outstanding work

1. `DASH-SHELL-1` — approved V7 application shell, authentication, six-screen navigation, persistent status.
2. `TXN-1` — append-only transaction ledger and correction chain.
3. `PORT-1` — holdings, basis, P/L, portfolio history, pricing/basis coverage.
4. `REC-UI-1` — domain-native recommendation and asset-detail experience.
5. `REFRESH-UI-1` — governed refresh/data-health orchestration experience.
6. `OPS-1` — preserve existing Render operational tooling under Operations.
7. `UIP_E1_STOCKS_ETF_EXTENSION_BOUNDARY` — integrate Stocks/ETF through approved contracts.
8. `DASH-CERT-1` — end-to-end Render usability and authority certification.
9. Final remote infrastructure selection and laptop-independent certification.

## Governance boundaries

Still prohibited unless separately governed and certified:

- universal cross-asset ranking;
- transfer of native ranks/scores across domains;
- cross-domain investment weighting or allocation policy;
- interpreting missing values as zero, worst rank, WAIT, HOLD, or any fabricated authority;
- automatic purchase or sale execution;
- treating model-qualified BUY candidates as execution-ready orders;
- silently redefining native recommendation, forecast, risk, or rank semantics.

Refresh remains separate from model retraining. Forecast-model validation remains separate from recommendation-policy validation.

## State principle

> UIP now has a certified R3 analytical foundation, an approved V7 dashboard target, and a certified hosted presentation/read-model boundary. DASH-SHELL-1 may now make that product visible without weakening the separation between certified analytical truth and user/application state.
