# UIP Dashboard Product Specification V1

## Purpose

Turn the certified UIP backend into a user-facing investment decision application on Render while preserving domain-native authority, lineage, freshness, and fail-closed behavior.

The dashboard must help the user answer five questions quickly:

1. What changed?
2. What deserves attention?
3. What does each certified domain recommend in its own terms?
4. What do I currently own and how is it performing?
5. Is the data current and trustworthy enough to act on?

## Product principles

### 1. Certified authority before presentation
The UI may display analytical recommendations, forecasts, ranks, risk, and freshness only when a certified domain/read-model authority exists.

### 2. Domain-native semantics are preserved
Crypto, Metals, MTG, and future Stocks/ETF do not need identical models, ranks, horizons, or recommendation vocabularies.

### 3. Missing stays missing
The UI must show unavailable / not certified / not supported. It may not translate missing values into zero, worst rank, WAIT, HOLD, or a fabricated forecast.

### 4. Recommendation is not execution
The product helps the user decide and records what the user actually did. It does not automatically purchase or sell assets.

### 5. Portfolio state comes from an auditable transaction ledger
CSV snapshots remain setup/reconciliation/recovery tools, but day-to-day ownership is derived from recorded transactions.

### 6. Refresh is fail-closed
A failed refresh leaves the last certified state active and visibly identifies the failure.

### 7. Future domains plug into contracts, not hard-coded pages
Stocks/ETF must be able to register into the same Home, Recommendations, Portfolio, Refresh, and Operations surfaces without redesigning the application.

---

## Primary navigation

1. Home
2. Recommendations
3. Portfolio
4. Transactions
5. Refresh
6. Operations

Forecasts and macro context are supporting views inside recommendation/asset detail rather than primary navigation.

---

## Global application shell

Every authenticated page should expose:

- UIP health
- last successful certified refresh
- active certified domains
- domains that are configured but not yet certified
- a clear stale/degraded indicator
- account/user menu
- responsive layout
- keyboard-accessible navigation

Prototype/demo values must be visually labeled as sample data.

---

## Home

### Goal
Answer: “What matters today?”

### Required components

#### Status strip
- UIP health
- last certified refresh
- active domains
- degraded/stale domain warnings
- read-model publication version

#### Quick actions
- Record Buy
- Record Sell
- View Recommendations
- Refresh All

#### Portfolio KPIs
- portfolio value
- total cost basis
- unrealized P/L
- realized P/L
- number of positions
- largest concentration

Do not show a synthetic cross-domain forecast or risk-adjusted return unless a separately governed portfolio-level methodology exists.

#### Primary decision panel
Shows one highest-priority decision item using UI relevance rules, not a universal investment rank.

Fields:
- asset
- domain
- native recommendation/status
- current price, if authoritative
- strongest supported horizon
- confidence, if authoritative
- “why now”
- user position
- portfolio impact estimate, if policy/portfolio math supports it
- freshness
- actions: detail, record buy/sell, watch

#### Top opportunities
Maximum 3–5 items. Must indicate whether sorting is:
- domain-native rank,
- user relevance,
- freshness/actionability,
- or a UI display helper.

#### What changed since last refresh
Decision-impacting deltas only:
- recommendation changes
- major forecast changes
- risk warnings
- stale/recovered data
- new/removed authority

#### Portfolio needs attention
Examples:
- concentration threshold exceeded
- recommendation deterioration
- stale data
- missing cost basis
- unpriced position
- refresh failure
- portfolio/recommendation conflict

#### Macro/context strip
Contextual only unless the underlying domain explicitly uses the macro inputs as model authority.

---

## Recommendations

### Goal
Answer: “What does UIP currently think I should review?”

### Filters
- domain
- recommendation/status
- owned/not owned
- confidence
- horizon
- freshness
- risk
- lane/subtype where relevant

### Recommendation card/table fields
- asset/product
- domain
- lane/subtype
- current authoritative price
- native recommendation/status
- supported forecast/horizon
- confidence/risk if supported
- owned quantity/value
- freshness
- authority state
- explanation
- special execution note
- actions

### Sorting
Do not call the list a universal ranking unless a governed cross-domain methodology exists.

Allowed UI sort helpers:
- actionability
- freshness
- ownership
- severity of change
- user watchlist state
- domain-native rank within a domain

### MTG rules
- expose Collector / Pre-Collector / Secret Lair lane
- preserve native rank semantics
- preserve tied ranks
- Secret Lair BUY candidate must show manual execution-price check requirement
- no automatic execution

### Future ETF rules
Until E1 certification:
- portfolio holdings may appear
- recommendation/forecast fields show “No certified recommendation”
- no fabricated BUY/HOLD/forecast values

---

## Asset / Recommendation Detail Drawer

### Goal
Answer: “Why is UIP saying this, what changed, and how does it relate to me?”

### Required sections
1. identity + domain + lane
2. current recommendation/status
3. price + freshness
4. supported horizons only
5. confidence interval only if the native authority publishes it
6. rationale
7. authority + lineage summary
8. recommendation history
9. user position
10. transaction history
11. portfolio impact
12. record buy/sell/watch actions

Unsupported horizons should be omitted or labeled unavailable, never extrapolated.

---

## Portfolio

### Goal
Answer: “What do I own and how is it doing?”

### Summary
- market value
- cost basis
- unrealized P/L
- realized P/L
- positions
- largest concentration

### Allocation
- by domain
- by account
- optionally by asset/subtype

Allocation is descriptive unless an explicit governed allocation policy exists.

### Holdings table
- asset
- domain
- lane/subtype
- account
- quantity
- basis status
- average cost
- current price
- market value
- unrealized P/L
- realized P/L
- weight
- current recommendation/status
- freshness

### Basis handling
Support:
- known basis
- gifted / inherited
- unknown basis
- partial basis
- fees

Do not treat unknown basis as zero economically; display basis state explicitly.

---

## Transactions

### Goal
Create the auditable source of portfolio ownership.

### Record transaction fields
- type: buy / sell / transfer / gift / adjustment
- domain
- asset
- date/time
- quantity
- price per unit
- fees
- currency
- account/location
- source/venue
- notes
- external order/reference ID optional

### Ledger rules
- append-only
- corrections create amendment/reversal entries
- no silent mutation of historical transactions
- user can view correction chain
- portfolio is recomputed from ledger

### MTG-specific needs
- sealed-unit quantities
- physical location/account
- marketplace fees
- shipping costs/proceeds
- gifted/basis-unknown support

### CSV snapshot importer
Keep only for:
- initial setup
- reconciliation
- recovery
- audit comparison

---

## Refresh & Data Health

### Goal
Answer: “Can I trust the displayed data right now?”

### Global actions
- Refresh All
- run scheduled refresh now
- last refresh log

### Per-domain card
- domain
- health
- last successful refresh
- data age
- next scheduled refresh
- current package/import
- current authority version
- refresh button
- last failure stage
- last-good-state status

### Lifecycle
Requested → Source Refresh → Certification → UIP Import → Activation → Complete

### Failure behavior
- never replace last certified state with failed output
- show failure stage
- show age of last certified state
- show whether recommendations remain usable
- preserve evidence

### External-source rule
UIP requests/dispatches governed source workflows; it does not duplicate or bypass source-owned collectors.

---

## Operations

### Goal
Provide technical evidence without overwhelming the investment workflow.

### Required components
- API health
- database health
- read-model publication state
- provider health
- import history
- package/import IDs
- domain registry status
- lineage
- warnings/errors
- refresh runs
- audit events
- current certified authority fingerprint/version

### Architectural separation
Analytical authority:
- certified UIP/domain outputs

Application state:
- transactions
- user settings
- watchlist
- UI preferences
- sessions

Render/PostgreSQL should consume a versioned published read model rather than independently reconstruct analytical authority.

---

## Watchlist and decision-state extension

Recommended V1 capability:
- Watch
- Dismiss for now
- Acted
- Review later

This is user workflow state, not analytical authority.

---

## Alerts / attention rules

The Home page should prioritize:
- new recommendation
- recommendation changed
- owned asset deteriorated
- concentration threshold breached
- stale domain
- refresh failed
- missing basis
- missing price
- execution-price check required
- previously acted recommendation materially changed

---

## Authentication / privacy

- authenticated dashboard
- credentials not exposed in page source
- least-privilege viewer/operator roles
- transaction writes require operator permission
- technical/admin details restricted when appropriate
- personal portfolio/transaction data kept separate from public analytical artifacts

---

## Responsive / accessibility requirements

- desktop-first but fully usable on tablet/mobile
- tables collapse to cards on narrow widths
- semantic labels are not color-only
- keyboard navigation
- visible focus states
- accessible status messages
- no critical data hidden only in hover tooltips

---

## Empty / degraded states

Every major widget must define:
- no portfolio yet
- no transactions yet
- no recommendation authority
- no price authority
- stale data
- failed refresh
- domain not active
- partial lineage
- read model unavailable

Fail closed and explain the state.

---

## V7 visual acceptance refinements

The approved visual acceptance target is `uip_dashboard_v7.html`. The following rules are part of the specification and are not optional cosmetic choices:

- the global status bar persists across all primary pages;
- benchmark comparison is historical/actual performance only unless a separate portfolio-level forecast model is governed and certified;
- portfolio value exposes current-price coverage;
- portfolio return exposes cost-basis coverage and is labeled as known-basis return when coverage is incomplete;
- unknown basis never becomes zero;
- native ranks are displayed exactly as published and UIP does not invent a denominator or compare native ranks across domains/lanes;
- the Home hero is selected by a deterministic presentation priority using actionability, material change, ownership relevance, and freshness, not a universal investment score;
- native source-domain status remains traceable separately from any user-facing display label;
- unsupported forecasts are hidden or explicitly unavailable; price history must never be styled or labeled as a forecast;
- portfolio-vs-benchmark visuals are context, not recommendations;
- degraded-state examples in prototypes must be labeled as illustrative and must not be confused with actual certified production state;
- the six primary navigation targets remain Home, Recommendations, Portfolio, Transactions, Refresh, and Operations.

## Acceptance criteria

Dashboard V1 is usable only when:

1. Home shows certified state and decision-impacting changes.
2. Recommendations preserve domain-native semantics.
3. No unsupported value is synthesized.
4. Portfolio is reproducible from the transaction ledger.
5. Transaction corrections are auditable.
6. Refresh can be requested from UI and failure preserves last-good authority.
7. Domain health/freshness is visible.
8. Asset detail shows rationale, history, authority, and user position.
9. Operations exposes sufficient lineage/import evidence.
10. Stocks/ETF can be added through domain contracts without redesigning the shell.
11. No automatic trade execution exists.
12. No universal cross-domain ranking/allocation is implied unless separately governed.

---

## Governing implementation sequence

1. DASH-SPEC-1 — freeze dashboard product specification
2. DASH-READ-1 — define certified presentation/read-model publication contract
3. DASH-SHELL-1 — implement application shell + auth + navigation
4. TXN-1 — implement append-only transaction ledger
5. PORT-1 — derive portfolio/current holdings from transactions
6. REC-UI-1 — implement recommendation/asset detail experience
7. REFRESH-UI-1 — implement refresh/data-health orchestration UI
8. OPS-1 — move current technical dashboard into Operations
9. E1 — integrate Stocks/ETF against the same contracts
10. DASH-CERT-1 — end-to-end Render usability and authority certification
