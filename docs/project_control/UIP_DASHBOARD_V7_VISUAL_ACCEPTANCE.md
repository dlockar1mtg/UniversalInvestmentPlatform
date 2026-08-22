# UIP Dashboard V7 — Visual Acceptance Record

## Status

`APPROVED_VISUAL_ACCEPTANCE_TARGET`

## Approved artifact

Filename:

`uip_dashboard_v7.html`

SHA-256:

`7403863ec8f662fbfbd293a3f19ac1d166dbde9bf79107da211f34da2c24d03a`

Approval date:

`2026-08-22`

Approval authority:

`Devon Lockard`

## Purpose

This record freezes the V7 mockup as the visual acceptance target for the user-facing UIP dashboard. Implementation may adapt internal code, APIs, storage, and responsive behavior, but material changes to information architecture, semantics, primary workflows, or governance behavior require a new approved change.

## Primary navigation

1. Home
2. Recommendations
3. Portfolio
4. Transactions
5. Refresh
6. Operations

## Required visual/product behavior

- persistent global UIP health/freshness bar across primary screens;
- Home prioritizes what changed and what needs attention;
- recommendation display preserves native domain semantics;
- no universal cross-domain rank is implied by UI ordering;
- MTG lane/rank semantics remain native and tied ranks remain valid;
- Secret Lair BUY candidates show manual execution-price verification requirements;
- future Stocks/ETF holdings may be tracked before recommendation authority exists, but unsupported recommendations/forecasts remain unavailable;
- portfolio value exposes pricing coverage;
- portfolio return exposes cost-basis coverage;
- unknown basis remains unknown rather than zero;
- portfolio-vs-S&P display is historical benchmark context unless a separately governed portfolio-level forecast model is later certified;
- asset detail distinguishes forecast, price history, and user performance since purchase;
- transaction history is append-only with explicit correction/amendment chains;
- Refresh shows Requested → Source Refresh → Certification → UIP Import → Activation → Complete and preserves last-good authority on failure;
- Operations preserves health, refresh-run, import, lineage, event/audit, and API-metric visibility;
- degraded-state examples in prototypes are illustrative and must never be confused with current certified production state;
- automatic purchase/sale execution remains unauthorized.

## Governing product specification

`docs/project_control/UIP_DASHBOARD_PRODUCT_SPEC_V1.md`

## Implementation rule

Future dashboard and Render work is evaluated against this approved visual target and the product specification. Backend implementation should serve the approved user workflow rather than redefine the dashboard opportunistically.

## Next gate

`DASH-READ-1 — CERTIFIED_PRESENTATION_READ_MODEL_PUBLICATION_CONTRACT`
