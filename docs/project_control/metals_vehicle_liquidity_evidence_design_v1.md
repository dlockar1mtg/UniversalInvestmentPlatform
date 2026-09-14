# Metals Vehicle Liquidity Evidence Design V1

## Objective

Define the liquidity / implementation-friction evidence required by `UIP_NATIVE_METALS_VEHICLE_RANKING_V1` without manufacturing market microstructure evidence from daily bars.

## Existing governed evidence

The certified Metals rich history already publishes daily vehicle observations under `UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1` with:

- ticker;
- observation date;
- close price;
- volume;
- source authority and package/run provenance.

That is sufficient to derive 30-session average dollar volume deterministically as `mean(close_usd * volume)` after resolving same-date revisions under the governed revision policy.

No separate market source is required for average dollar volume.

## Average dollar volume authority

For each of the 10 registered commodity implementation vehicles (GLD, IAU, SGOL, SLV, SIVR, PPLT, CPER, COPX, URA, URNM):

1. select the latest governed source revision for each ticker/trading session;
2. require at least 30 distinct valid sessions;
3. calculate daily dollar volume as `close_usd * volume`;
4. calculate 30-session ADV as the arithmetic mean of those 30 daily dollar-volume observations;
5. retain start date, end date, observation count, source authority, and source run/package provenance.

Missing close or volume does not become zero and cannot be backfilled from another ticker.

## Bid/ask spread evidence

Daily OHLCV does **not** contain quoted bid and ask and therefore cannot certify implementation spread.

UIP requires a separately governed quote source that supplies, at minimum:

- ticker;
- trading date;
- bid;
- ask;
- observation timestamp;
- source authority/provenance.

For each valid quote observation:

`relative_spread_bps = ((ask - bid) / ((ask + bid) / 2)) * 10000`

The ranking input is the median relative spread across the latest 20 trading sessions with valid governed observations.

At least 20 sessions are required for each compared vehicle.

## Prohibited spread proxies

The following may not be labeled or substituted as bid/ask spread:

- daily high-low range;
- close-to-close volatility;
- ATR;
- turnover or volume alone;
- issuer-reported average spread without explicit governed provenance and period semantics;
- missing values filled with zero or a peer value.

## Ranking boundary

ADV coverage alone does not authorize the liquidity component of the vehicle ranking. Both 30-session ADV and 20-session median quoted spread must be complete for every vehicle in the commodity comparison group.

If spread evidence is missing, the vehicle may remain a registered implementation candidate, but `PREFERRED IMPLEMENTATION CANDIDATE` remains blocked.

## Current authorization decision

- derive ADV from existing certified vehicle history: **AUTHORIZED FOR READ-ONLY REHEARSAL**;
- manufacture spread from daily history: **PROHIBITED**;
- collect governed quote evidence: **REQUIRES SEPARATE SOURCE/COLLECTION AUTHORIZATION**;
- preferred vehicle ranking: **FAIL-CLOSED UNTIL REQUIRED EVIDENCE IS COMPLETE**.

## Governance boundary

This design does not modify the Metals source collection schedule, publish new presentation rows, create a preferred vehicle result, authorize allocation or execution, or restore the central publication cron.
