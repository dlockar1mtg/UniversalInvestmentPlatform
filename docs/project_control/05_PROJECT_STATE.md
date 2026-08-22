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
CERTIFIED_DOMAIN_INTEGRATION_SEQUENCE_ACTIVE

Current roadmap phase:
Certified domain integration

Current milestone:
UIP_E1_STOCKS_ETF_EXTENSION_BOUNDARY

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

Next authorized action:
EXECUTE_UIP_E1_STOCKS_ETF_EXTENSION_BOUNDARY
```

## Repository authority

Primary repository:

`dlockar1mtg/UniversalInvestmentPlatform`

Stable branch:

`main`

Current closeout branch:

`phase-uip-r3-cross-domain-closeout`

R3 closeout implementation/evidence baseline before final closeout commits:

`7c94b0a97cd60c3145da8265fd092ec7e216e36e`

Current certified authoritative UIP database SHA-256:

`9af5e52882bdf61fed550a2ced9bc83ba1529c422633a7817660cf61d0e15a98`

Pre-migration-010 backup SHA-256:

`df7406361639e4b165afb8007f97feca60242e91d290c58ae521e423d82578cc`

Database classification:

`AUTHORITATIVE_MULTI_DOMAIN_PRODUCTION_STATE — R3_CERTIFIED`

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

Crypto native recommendation semantics remain Crypto-owned. R3 created no cross-domain rank or allocation policy.

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

Secret Lair remains a dynamic population. BUY candidates do not constitute execution authority.

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

Append-only history populations at R3 closeout:

- asset master history: `8,199`
- forecasts history: `5,254`
- recommendations history: `5,285`
- risk metrics history: `2,439`
- platform-status history: `25`
- MTG native-authority history: `968`

Permanent evidence:

`docs/project_control/generated/r3_cross_domain_closeout/r3_cross_domain_closeout_certification.json`

Human-readable closeout:

`docs/project_control/R3_CROSS_DOMAIN_CLOSEOUT.md`

Disposition:

`UIP_R3_CERTIFIED_COMPLETE`

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

## Protected recovery resources

Historical recovery branches, archives, and local recovery resources remain evidence. They are not authorized for wholesale merge or destructive cleanup solely because R3 is complete.

Previously identified protected local resources remain protected from unrelated work:

- `export_uip_interpretation_data.py`
- `uip_interpretation_export/`
- `uip_interpretation_input/`
- `uip_recovery_inspection/`
- `uip_recovery_inspection_output.txt`

Detailed historical recovery findings and prior transition records remain available in repository history and the permanent certification evidence under `docs/project_control/generated/`.

## Current risks and outstanding work

1. Stocks/ETF extension must be integrated under its own domain-native authority and certification.
2. Phase 11 cross-domain production automation may be selectively ported only after review against the certified R3 architecture.
3. Dashboard and user-facing service completion remain outstanding.
4. Remote infrastructure selection and laptop-independent production certification remain outstanding.
5. Protected personal financial/recovery snapshots must remain outside repository publication boundaries.

## Next integration sequence

1. `UIP_E1_STOCKS_ETF_EXTENSION_BOUNDARY` — define and certify the Stocks/ETF domain boundary without inheriting other-domain models or rankings.
2. Continue remaining priority-domain integrations under domain-native governance as authorized.
3. Evaluate selective Phase 11 automation after the certified domain set is ready.
4. `UIP_DASH-1` and `UIP_DASH-2` — build the dashboard on certified multi-domain authority.
5. Complete remote infrastructure and laptop-independent production certification.
6. Govern any future cross-asset ranking, comparison, or allocation methodology separately.

## State principle

> UIP recovery history remains preserved, but current integration proceeds from certified repository and domain-package authority. Each domain retains its native semantics; UIP may accept certified outputs, preserve lineage, orchestrate governed refreshes, and present evidence without silently redefining native models, ranks, recommendations, or execution authority.
