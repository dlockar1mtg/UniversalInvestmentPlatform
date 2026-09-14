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

## Bid/ask spread source authority

Daily OHLCV does **not** contain quoted bid and ask and therefore cannot certify implementation spread.

Alpaca Market Data using the `sip` feed is the certified quote-provider source based on the verified manual suitability rehearsal. Silent downgrade to IEX remains prohibited.

The quote evidence must retain, at minimum:

- ticker;
- trading date;
- bid;
- ask;
- observation timestamp;
- source authority;
- feed;
- source run provenance.

For each valid quote observation:

`relative_spread_bps = ((ask - bid) / ((ask + bid) / 2)) * 10000`

## Session-balanced spread methodology

The ranking input is not computed by pooling every raw quote across 20 sessions.

For each ticker and each valid trading session:

1. use only valid SIP quotes timestamped from 15:50:00 through 16:00:00 America/New_York;
2. require finite positive bid and ask with `ask >= bid`;
3. calculate `relative_spread_bps` for each valid quote;
4. calculate one session statistic: the median relative spread across all valid quotes in that session window;
5. retain session date, valid quote count, first/last timestamps, source authority, feed, and source run provenance.

The final vehicle spread metric is the median of those session medians across the latest 20 distinct valid trading sessions.

At least 20 valid sessions are required for each compared vehicle. Each session therefore receives one equal contribution regardless of raw quote-update frequency.

Weekends and exchange holidays do not count as trading sessions. Candidate dates with no valid SIP quotes are skipped and may not be converted to zero or replaced with another ticker's value. The collector may probe farther backward within the separately governed bounded search window to establish 20 valid sessions.

The detailed authority is `docs/project_control/metals_vehicle_spread_sampling_methodology_v1.md`.

## Prohibited spread proxies and shortcuts

The following may not be labeled or substituted as the governed bid/ask spread metric:

- daily high-low range;
- close-to-close volatility;
- ATR;
- turnover or volume alone;
- issuer-reported average spread without explicit governed provenance and period semantics;
- every raw quote from all sessions pooled without equal session weighting;
- a first-quote-only or last-quote-only shortcut without a separately versioned methodology;
- IEX fallback;
- missing values filled with zero or a peer value.

## Ranking boundary

ADV coverage alone does not authorize the liquidity component of the vehicle ranking. Both 30-session ADV and 20-session median-of-session-medians quoted spread must be complete for every vehicle in the commodity comparison group.

If spread evidence is missing, the vehicle may remain a registered implementation candidate, but `PREFERRED IMPLEMENTATION CANDIDATE` remains blocked.

## Current authorization decision

- derive ADV from existing certified vehicle history: **AUTHORIZED FOR READ-ONLY REHEARSAL**;
- Alpaca SIP provider suitability: **CERTIFIED**;
- session-balanced spread methodology: **GOVERNED**;
- production quote collection: **NOT AUTHORIZED**;
- bounded read-only spread-evidence rehearsal: **NEXT GATE**;
- preferred vehicle ranking: **FAIL-CLOSED UNTIL REQUIRED EVIDENCE IS COMPLETE**.

## Governance boundary

This design does not modify the Metals source collection schedule, publish new presentation rows, create a preferred vehicle result, authorize allocation or execution, or restore the central publication cron.
