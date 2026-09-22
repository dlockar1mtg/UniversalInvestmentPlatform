# DASH-CERT-1 — End-to-End Dashboard Production Acceptance

## Status

`DASH_CERT_1_ACCEPTED_COMPLETE`

Acceptance date: 2026-09-22

Accepted application commit:

`e26181e3d328d453aee1581c79e14f68dac3d40f`

Accepted active hosted publication:

- publication ID: `uip-rich-production-20260921T200442Z-2ed557a8e134`
- version: `1.0.0`
- records: `14309`
- content fingerprint: `90de48bf27cce58de2f7e4c7ba7e936d0d5c26a800b95a4a0ea323128abfbd70`
- source database SHA-256: `2ed557a8e134cd29812579e0fa220e36c17c593b0b27190e4e5339d9a8ce169b`

## Scope accepted

The user explicitly accepted the six primary hosted application surfaces as sufficiently complete for the current UIP product baseline:

1. Home
2. Recommendations
3. Portfolio
4. Transactions
5. Refresh & Data Health
6. Operations

The accepted shell preserves the approved primary navigation and the certified presentation boundary.

## Production acceptance evidence

### Home

Accepted behavior:

- overall tracked portfolio summary is shown at the top of the page;
- certified PORT-1 holdings, Acorns, and manually tracked stock/ETF snapshots are combined only for the personal overview;
- total current value, cost basis, gain/loss, return, tracked components, and largest allocation are visible;
- quick actions route to transaction entry, recommendations, and data health;
- decision-impacting attention is driven by operational/freshness and portfolio-coverage state rather than a universal investment ranking;
- certified domain status remains visible as supporting authority.

Hosted acceptance values observed on 2026-09-22:

- tracked components: `30`
- total current value: `6802.39 USD`
- total cost basis: `6232.54 USD`
- gain/loss: `+569.84 USD`
- overall return: `+9.14%`
- largest allocation: `MTG 51.8%`

### Recommendations

Accepted behavior:

- Crypto, Metals, and MTG remain domain-native research systems;
- no universal cross-domain rank or automatic execution is created;
- certified forecast/risk/recommendation evidence is presented using native domain semantics;
- unsupported analytical fields remain absent/unavailable rather than synthesized.

### Portfolio

Accepted behavior:

- certified PORT-1 ownership is derived from the append-only transaction ledger;
- external Acorns and manual stock/ETF snapshots remain clearly separated from certified PORT-1 authority;
- the personal overall portfolio combines these sources only as a mixed-authority user summary;
- pricing and basis coverage are explicit;
- unknown/unavailable values remain fail-closed.

Hosted acceptance values observed on 2026-09-22:

- certified PORT-1 positions: `25`
- effective transactions: `27`
- superseded transactions: `5`
- pricing coverage: `25/25`
- basis coverage: `25/25`
- certified PORT-1 market value: `4751.14 USD`
- manual stock/ETF positions: `4`
- manual stock/ETF value: `662.41 USD`
- Acorns value: `1388.84 USD`

### Transactions

Accepted behavior:

- transaction history is retained append-only;
- corrections preserve the corrected transaction and add a correction entry rather than silently mutating history;
- filtering/search remain available;
- transaction entry is integrated with current portfolio context;
- portfolio accounting is recomputed from effective ledger history.

Hosted acceptance state observed on 2026-09-22:

- retained transactions: `32`
- reconciliation: `27 effective + 5 superseded = 32 retained`

### Refresh & Data Health

Accepted behavior:

- operational health is separated from data freshness;
- last-good certified authority remains active when freshness metadata is stale/unknown;
- source-owned schedules, last import, next scheduled run, package/import lineage, and lifecycle are visible;
- refresh remains separate from model retraining;
- hosted UI does not bypass source-owned collectors.

Known accepted deferred metadata cleanup:

- Metals reports `DATA STALE` because the active authority reports data-as-of `2026-08-01`;
- MTG reports `DATA UNKNOWN` because its active authority does not publish a governed data-as-of value;
- these are metadata/freshness-authority follow-ups, not failed production imports;
- manual source-workflow dispatch is not yet exposed from the hosted UI.

These deferred items do not invalidate the accepted current dashboard baseline.

### Operations

Accepted behavior:

- API service, database readiness, read-model state, providers, publication lineage, domain registry, refresh evidence, audit events, and API metrics are grouped under Operations;
- the active publication ID/version/fingerprint/source SHA are visible;
- legacy CSV portfolio state is retained only under Advanced recovery / legacy reconciliation;
- legacy CSV state is not represented as live ownership authority;
- in-memory counters are labeled as since-service-start diagnostics.

Hosted acceptance state observed on 2026-09-22:

- API service: `LIVE`
- database: `READY`
- read model: `ACTIVE`
- providers: `2/2`
- domain registry: `3/3 healthy`

## Governance assertions

DASH-CERT-1 certifies the hosted product behavior above and preserves these non-negotiable boundaries:

- no universal cross-domain recommendation rank;
- no universal allocation policy;
- no automatic trading or purchasing;
- no unsupported forecast synthesis;
- no conversion of missing values into zero/HOLD/WAIT;
- no mutation of historical transaction rows;
- no promotion of manual external holdings into certified analytical authority;
- no promotion of the legacy CSV snapshot into ownership authority;
- no replacement of last-good certified authority by a failed refresh;
- no bypass of source-owned refresh collectors.

## Deferred non-blocking follow-up

The following are explicitly outside the accepted completion gate and may be handled later without reopening DASH-CERT-1:

1. repair Metals source metadata so its true current data-as-of value is published;
2. add governed MTG data-as-of metadata;
3. expose governed source-workflow dispatch from Refresh when an approved dispatch service exists;
4. improve persistent operational instrumentation beyond in-memory request/event counters;
5. continue future analytical-domain work such as Stocks/ETF through approved domain-neutral contracts;
6. complete remote-production/laptop-independence hardening under the later infrastructure gate.

## Certification boundary

DASH-CERT-1 certifies the user-facing dashboard application baseline at accepted application commit:

`e26181e3d328d453aee1581c79e14f68dac3d40f`

The certification artifact itself may merge after that commit; the accepted application commit remains the immutable product baseline for this gate.

Next roadmap gate after DASH-CERT-1:

`UIP_REMOTE_PRODUCTION_CERTIFIED`
